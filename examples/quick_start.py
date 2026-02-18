"""Quick-start example for the TickTick SDK.

Demonstrates the most common workflow:
  1. Authenticate with a session token.
  2. List all projects.
  3. Create a task with subtasks in a chosen project.
  4. Mark the task as completed.
  5. Delete the task.

Set the TICKTICK_TOKEN environment variable to your TickTick session
token before running this script.  You can obtain the token from the
browser's DevTools (Application -> Cookies -> ticktick.com -> "t").

Expected output:
    Projects (4):
      - Inbox                [id: 6502a1...]
      - Work                 [id: 6502b3...]
      - Personal             [id: 6502c7...]
      - Shopping             [id: 6502d1...]

    Created task: "Prepare weekly report" (id: a1b2c3d4e5f6)
      Subtask: "Collect metrics"
      Subtask: "Write summary"
      Subtask: "Send to manager"

    Task completed.
    Task deleted.
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

    # 1. List all projects
    projects = client.project.get_all()
    print(f"Projects ({len(projects)}):")
    for p in projects:
        print(f"  - {p.name:<22} [id: {p.id[:6]}...]")

    # Pick the inbox (or fall back to the first project)
    target = next((p for p in projects if p.name.lower() == "inbox"), projects[0])

    # 2. Create a task with three subtasks
    task = client.task.create(
        "Prepare weekly report",
        project_id=target.id,
        priority=3,  # medium
        tags=["work", "report"],
        items=[
            {"title": "Collect metrics"},
            {"title": "Write summary"},
            {"title": "Send to manager"},
        ],
    )
    print(f"\nCreated task: \"{task.title}\" (id: {task.id})")
    for sub in task.items:
        print(f"  Subtask: \"{sub.title}\"")

    # 3. Complete the task
    client.task.complete(task.id, task.project_id)
    print("\nTask completed.")

    # 4. Delete the task
    client.task.delete(task.id, task.project_id)
    print("Task deleted.")


if __name__ == "__main__":
    main()
