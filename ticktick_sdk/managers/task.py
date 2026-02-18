"""Task management - CRUD for tasks, subtasks, and batch operations."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ticktick_sdk.models import Task, Subtask

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class TaskManager:
    """Manage tasks, subtasks, completion, and trash."""

    def __init__(self, client: TickTickClient):
        self._c = client

    # ── Read ──────────────────────────────────────────────────────────

    def get(self, task_id: str, project_id: str) -> Task:
        """Get a single task by ID.

        Args:
            task_id: The task ID.
            project_id: The project (list) ID the task belongs to.
        """
        resp = self._c.get(f"/api/v2/task/{task_id}", params={"projectId": project_id})
        return Task.from_dict(resp.json())

    def get_all(self) -> list[Task]:
        """Get all tasks via batch sync (returns open tasks from all projects)."""
        data = self._c.batch.check()
        tasks_raw = data.get("syncTaskBean", {}).get("update", [])
        return [Task.from_dict(t) for t in tasks_raw]

    def get_by_project(self, project_id: str) -> list[Task]:
        """Get all open tasks in a project."""
        all_tasks = self.get_all()
        return [t for t in all_tasks if t.project_id == project_id]

    def get_completed(
        self,
        project_id: str | None = None,
        *,
        from_date: str = "",
        to_date: str = "",
        limit: int = 50,
    ) -> list[Task]:
        """Get completed tasks, optionally filtered by project and date range.

        Args:
            project_id: Filter to a specific project. None returns all.
            from_date: Start date as "YYYY-MM-DD HH:MM:SS" (inclusive).
            to_date: End date as "YYYY-MM-DD HH:MM:SS" (inclusive).
            limit: Maximum number of results.
        """
        if project_id:
            endpoint = f"/api/v2/project/{project_id}/completed/"
        else:
            endpoint = "/api/v2/project/all/completed/"
        params: dict[str, Any] = {"limit": limit}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        resp = self._c.get(endpoint, params=params)
        return [Task.from_dict(t) for t in resp.json()]

    def get_completed_in_all(
        self,
        from_date: str = "",
        to_date: str = "",
        limit: int = 1200,
    ) -> list[Task]:
        """Get completed tasks across all lists (broader query)."""
        params: dict[str, Any] = {"limit": limit}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        resp = self._c.get("/api/v2/project/all/completedInAll/", params=params)
        return [Task.from_dict(t) for t in resp.json()]

    def get_trash(self, limit: int = 50) -> list[Task]:
        """Get tasks in trash."""
        resp = self._c.get("/api/v2/project/all/trash/pagination", params={"limit": limit})
        data = resp.json()
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        return [Task.from_dict(t) for t in tasks]

    # ── Create ────────────────────────────────────────────────────────

    def create(
        self,
        title: str,
        *,
        project_id: str | None = None,
        content: str = "",
        desc: str = "",
        priority: int = 0,
        tags: list[str] | None = None,
        start_date: datetime | None = None,
        due_date: datetime | None = None,
        is_all_day: bool = False,
        time_zone: str = "",
        repeat_flag: str = "",
        items: list[dict[str, Any]] | None = None,
        reminders: list[dict[str, str]] | None = None,
        parent_id: str = "",
        column_id: str = "",
        kind: str = "TEXT",
        sort_order: int = 0,
    ) -> Task:
        """Create a new task.

        Args:
            title: Task title.
            project_id: Project/list ID. Defaults to inbox.
            content: Task body/notes (markdown supported).
            desc: Short description.
            priority: 0=none, 1=low, 3=medium, 5=high.
            tags: List of tag names.
            start_date: Start datetime.
            due_date: Due datetime.
            is_all_day: Whether this is an all-day event.
            time_zone: Timezone string e.g. "America/New_York".
            repeat_flag: iCal RRULE e.g. "RRULE:FREQ=DAILY;INTERVAL=1".
            items: List of subtask dicts with at least {"title": "..."}.
            reminders: List of reminder dicts with {"id": "...", "trigger": "..."}.
            parent_id: Parent task ID for creating child/sub tasks.
            column_id: Kanban column ID.
            kind: "TEXT" or "NOTE".
            sort_order: Sort order value.

        Returns:
            The created Task object.
        """
        task_id = os.urandom(12).hex()
        if project_id is None:
            project_id = self._c.inbox_id or "inbox"

        payload: dict[str, Any] = {
            "id": task_id,
            "projectId": project_id,
            "title": title,
            "content": content,
            "desc": desc,
            "priority": priority,
            "status": 0,
            "isAllDay": is_all_day,
            "kind": kind,
            "sortOrder": sort_order,
            "items": [],
            "reminders": [],
            "tags": tags or [],
        }
        if time_zone:
            payload["timeZone"] = time_zone
        if start_date:
            payload["startDate"] = start_date.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        if due_date:
            payload["dueDate"] = due_date.strftime("%Y-%m-%dT%H:%M:%S.000+0000")
        if repeat_flag:
            payload["repeatFlag"] = repeat_flag
        if parent_id:
            payload["parentId"] = parent_id
        if column_id:
            payload["columnId"] = column_id
        if items:
            for i, item in enumerate(items):
                item_id = item.get("id", os.urandom(12).hex())
                payload["items"].append({
                    "id": item_id,
                    "title": item["title"],
                    "status": item.get("status", 0),
                    "sortOrder": item.get("sortOrder", i * 1099511627776),
                    "isAllDay": False,
                })
        if reminders:
            payload["reminders"] = reminders

        resp = self._c.post("/api/v2/task", json=payload)
        return Task.from_dict(resp.json())

    # ── Update ────────────────────────────────────────────────────────

    def update(self, task: Task) -> Task:
        """Update an existing task. Pass a modified Task object.

        Returns the updated Task.
        """
        resp = self._c.post(
            f"/api/v2/task/{task.id}",
            json=task.to_dict(),
            params={"projectId": task.project_id},
        )
        return Task.from_dict(resp.json())

    def update_fields(self, task_id: str, project_id: str, **fields: Any) -> dict:
        """Partial update - fetch the task, merge fields, and save.

        Accepts any Task field in snake_case (e.g. title, priority, tags).
        """
        task = self.get(task_id, project_id)
        for key, val in fields.items():
            if hasattr(task, key):
                setattr(task, key, val)
        return self.update(task).to_dict()

    # ── Complete / Uncomplete ─────────────────────────────────────────

    def complete(self, task_id: str, project_id: str) -> Task:
        """Mark a task as completed."""
        task = self.get(task_id, project_id)
        task.status = 2
        return self.update(task)

    def uncomplete(self, task_id: str, project_id: str) -> Task:
        """Mark a completed task as open again."""
        task = self.get(task_id, project_id)
        task.status = 0
        return self.update(task)

    # ── Delete ────────────────────────────────────────────────────────

    def delete(self, task_id: str, project_id: str) -> None:
        """Delete a task (move to trash)."""
        self._c.post("/api/v2/batch/task", json={
            "delete": [{"taskId": task_id, "projectId": project_id}],
        })

    def batch_delete(self, tasks: list[dict[str, str]]) -> None:
        """Delete multiple tasks.

        Args:
            tasks: List of {"taskId": "...", "projectId": "..."} dicts.
        """
        self._c.post("/api/v2/batch/task", json={"delete": tasks})

    # ── Subtask helpers ───────────────────────────────────────────────

    def add_subtask(self, task_id: str, project_id: str, title: str, **kwargs: Any) -> Task:
        """Add a subtask (checklist item) to a task.

        Returns the updated parent task.
        """
        task = self.get(task_id, project_id)
        item_id = os.urandom(12).hex()
        max_order = max((i.sort_order for i in task.items), default=-1099511627776)
        new_item = Subtask(
            id=item_id,
            title=title,
            sort_order=max_order + 1099511627776,
            **kwargs,
        )
        task.items.append(new_item)
        return self.update(task)

    def complete_subtask(self, task_id: str, project_id: str, subtask_id: str) -> Task:
        """Mark a subtask as completed."""
        task = self.get(task_id, project_id)
        for item in task.items:
            if item.id == subtask_id:
                item.status = 2
                item.completed_time = datetime.now(timezone.utc)
                break
        return self.update(task)

    def remove_subtask(self, task_id: str, project_id: str, subtask_id: str) -> Task:
        """Remove a subtask from a task."""
        task = self.get(task_id, project_id)
        task.items = [i for i in task.items if i.id != subtask_id]
        return self.update(task)

    # ── Batch operations ──────────────────────────────────────────────

    def batch_create(self, tasks: list[dict[str, Any]]) -> dict:
        """Create multiple tasks in one request.

        Args:
            tasks: List of task dicts (same format as create() payload).
        """
        return self._c.post("/api/v2/batch/task", json={"add": tasks}).json()

    def batch_update(self, tasks: list[dict[str, Any]]) -> dict:
        """Update multiple tasks in one request."""
        return self._c.post("/api/v2/batch/task", json={"update": tasks}).json()

    def move(self, task_id: str, from_project: str, to_project: str) -> Task:
        """Move a task to a different project."""
        task = self.get(task_id, from_project)
        task.project_id = to_project
        return self.update(task)

    def set_parent(self, task_id: str, project_id: str, parent_id: str) -> dict:
        """Set a task as a child of another task (nested tasks)."""
        return self._c.post(
            "/api/v2/batch/taskParent",
            json=[{"taskId": task_id, "projectId": project_id, "parentId": parent_id}],
        ).json()
