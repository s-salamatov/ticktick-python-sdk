"""Bulk operations example for the TickTick SDK.

Demonstrates batch workflows that minimise round-trips to the API:
  1. Batch-create several tasks spread across two projects.
  2. Add tags to tasks to categorise them.
  3. Move a task from one project to another.
  4. Batch-complete a set of tasks.
  5. Batch-delete all tasks created during the demo.

Set the TICKTICK_TOKEN environment variable to your TickTick session
token before running this script.

Expected output:
    Projects found: Work (6502b3...), Personal (6502c7...)

    Batch-created 5 tasks.

    Tagged "Buy groceries" with ['personal', 'errands'].
    Tagged "Finish Q2 report" with ['work', 'quarterly'].

    Moved "Team standup notes" -> Personal (was Work).

    Completed 3 tasks.

    Deleted 5 tasks. Done.
"""

import os
import sys

from ticktick_sdk import TickTickClient


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

    # Find (or fall back to) two distinct projects to spread tasks across
    projects = client.project.get_all()
    work_project = next((p for p in projects if "work" in p.name.lower()), projects[0])
    personal_project = next(
        (p for p in projects if p.id != work_project.id), projects[-1]
    )
    print(
        f"Projects found: {work_project.name} ({work_project.id[:6]}...), "
        f"{personal_project.name} ({personal_project.id[:6]}...)"
    )

    # 1. Batch-create multiple tasks across both projects
    task_specs = [
        {"title": "Finish Q2 report",       "projectId": work_project.id,     "priority": 5},
        {"title": "Team standup notes",      "projectId": work_project.id,     "priority": 1},
        {"title": "Code review: auth module","projectId": work_project.id,     "priority": 3},
        {"title": "Buy groceries",           "projectId": personal_project.id, "priority": 1},
        {"title": "Book dentist appointment","projectId": personal_project.id, "priority": 0},
    ]
    client.task.batch_create(task_specs)
    print(f"\nBatch-created {len(task_specs)} tasks.")

    # Reload to get server-assigned IDs
    all_tasks = client.task.get_all()
    titles = {s["title"] for s in task_specs}
    created = [t for t in all_tasks if t.title in titles]

    # 2. Tag individual tasks
    for task in created:
        if task.project_id == personal_project.id and "grocery" in task.title.lower():
            task.tags = ["personal", "errands"]
            client.task.update(task)
            print(f"Tagged \"{task.title}\" with {task.tags}.")
        elif task.project_id == work_project.id and "Q2" in task.title:
            task.tags = ["work", "quarterly"]
            client.task.update(task)
            print(f"Tagged \"{task.title}\" with {task.tags}.")

    # 3. Move one task between projects
    standup = next((t for t in created if "standup" in t.title.lower()), None)
    if standup:
        client.task.move(standup.id, work_project.id, personal_project.id)
        print(f"\nMoved \"{standup.title}\" -> {personal_project.name} (was {work_project.name}).")

    # 4. Batch-complete the first three tasks
    to_complete = created[:3]
    updates = [{"id": t.id, "projectId": t.project_id, "status": 2} for t in to_complete]
    client.task.batch_update(updates)
    print(f"\nCompleted {len(to_complete)} tasks.")

    # 5. Batch-delete everything created in this demo
    to_delete = [{"taskId": t.id, "projectId": t.project_id} for t in created]
    client.task.batch_delete(to_delete)
    print(f"\nDeleted {len(to_delete)} tasks. Done.")


if __name__ == "__main__":
    main()
