"""Daily review script for the TickTick SDK.

Prints a concise productivity summary for the current day:
  1. Tasks due today (open).
  2. Overdue tasks (past due date, still open).
  3. Count of tasks completed today.
  4. Active habits with today's check-in status.

Designed to be run each morning or as a scheduled cron job.
Set the TICKTICK_TOKEN environment variable to your TickTick session
token before running.

Expected output:
    === Daily Review: 2026-02-18 ===

    Due today (2):
      [ ] Write sprint retrospective  [Work]     priority=medium
      [ ] Pay electricity bill        [Personal] priority=high

    Overdue (3):
      [ ] Update project roadmap      [Work]     due 2026-02-15
      [ ] Call accountant             [Personal] due 2026-02-16
      [ ] Review pull requests        [Work]     due 2026-02-17

    Completed today: 5 tasks

    Active habits (3):
      - Morning meditation    (daily)   checked-in today: yes
      - Exercise 30 min       (daily)   checked-in today: no
      - Read 20 pages         (daily)   checked-in today: yes
"""

import os
import sys
from datetime import date, datetime, timezone

from ticktick_sdk import TickTickClient

PRIORITY_LABEL = {0: "none", 1: "low", 3: "medium", 5: "high"}


def parse_due(due_str: str | None) -> datetime | None:
    """Parse a TickTick due-date string into a timezone-aware datetime."""
    if not due_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.000+0000", "%Y-%m-%dT%H:%M:%S+0000"):
        try:
            dt = datetime.strptime(due_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def main() -> None:
    token = os.environ.get("TICKTICK_TOKEN")
    if not token:
        print(
            "Error: TICKTICK_TOKEN environment variable is not set.\n"
            "Export your TickTick session token, e.g.:\n"
            "  export TICKTICK_TOKEN=your_token_here"
        )
        sys.exit(1)

    client = TickTickClient(token=token)

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)

    print(f"\n=== Daily Review: {today_str} ===")

    # Build a project name lookup for display
    projects = client.project.get_all()
    project_name = {p.id: p.name for p in projects}

    # 1. All open tasks (status=0) that have a due date
    due_tasks = client.search.filter_tasks(status=0, has_due_date=True)

    tasks_due_today = [
        t for t in due_tasks
        if parse_due(t.due_date) and parse_due(t.due_date).date() == today
    ]
    overdue_tasks = [
        t for t in due_tasks
        if parse_due(t.due_date) and parse_due(t.due_date) < now
        and parse_due(t.due_date).date() < today
    ]

    print(f"\nDue today ({len(tasks_due_today)}):")
    if tasks_due_today:
        for t in tasks_due_today:
            pname = project_name.get(t.project_id, t.project_id)
            print(f"  [ ] {t.title:<35} [{pname}]  priority={PRIORITY_LABEL.get(t.priority, t.priority)}")
    else:
        print("  (none)")

    print(f"\nOverdue ({len(overdue_tasks)}):")
    if overdue_tasks:
        for t in sorted(overdue_tasks, key=lambda t: t.due_date or ""):
            due_dt = parse_due(t.due_date)
            due_label = due_dt.strftime("%Y-%m-%d") if due_dt else "unknown"
            print(f"  [ ] {t.title:<35} due {due_label}")
    else:
        print("  (none)")

    # 2. Completed today
    start_of_day = today.strftime("%Y-%m-%d 00:00:00")
    end_of_day   = today.strftime("%Y-%m-%d 23:59:59")
    completed_today = client.task.get_completed(
        from_date=start_of_day,
        to_date=end_of_day,
        limit=200,
    )
    print(f"\nCompleted today: {len(completed_today)} tasks")

    # 3. Active habits with today's check-in status
    active_habits = client.habit.get_active()
    today_stamp = today.strftime("%Y%m%d")
    checkins = client.habit.get_checkins(
        habit_ids=[h.id for h in active_habits] if active_habits else None,
        after_stamp=today_stamp,
    )
    checked_today = {c.habit_id for c in checkins if c.checkin_stamp == today_stamp and c.status == 2}

    print(f"\nActive habits ({len(active_habits)}):")
    if active_habits:
        for h in active_habits:
            status = "yes" if h.id in checked_today else "no"
            print(f"  - {h.name:<26} checked-in today: {status}")
    else:
        print("  (no active habits)")


if __name__ == "__main__":
    main()
