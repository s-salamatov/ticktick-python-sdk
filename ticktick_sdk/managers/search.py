"""Search and filtering functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ticktick_sdk.models import Task

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class SearchManager:
    """Full-text search across tasks, tags, and lists."""

    def __init__(self, client: TickTickClient):
        self._c = client

    def search(self, keywords: str) -> dict:
        """Cloud search across all tasks, tags, lists, and filters.

        Args:
            keywords: Search query string.

        Returns:
            Raw API response containing matched tasks, tags, lists, etc.
        """
        return self._c.get("/api/v2/search/all", params={"keywords": keywords}).json()

    def search_tasks(self, keywords: str) -> list[Task]:
        """Search for tasks by keywords. Returns Task objects."""
        data = self.search(keywords)
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        return [Task.from_dict(t) for t in tasks]

    def filter_tasks(
        self,
        *,
        project_id: str | None = None,
        tag: str | None = None,
        priority: int | None = None,
        status: int | None = None,
        has_due_date: bool | None = None,
    ) -> list[Task]:
        """Filter tasks from the local batch data using criteria.

        This is a client-side filter over the batch sync data.

        Args:
            project_id: Filter to a specific project.
            tag: Filter by tag name.
            priority: Filter by priority (0, 1, 3, 5).
            status: Filter by status (0=open, 2=completed).
            has_due_date: Filter tasks with/without due dates.
        """
        tasks = self._c.task.get_all()
        if project_id is not None:
            tasks = [t for t in tasks if t.project_id == project_id]
        if tag is not None:
            tasks = [t for t in tasks if tag in t.tags]
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if has_due_date is True:
            tasks = [t for t in tasks if t.due_date is not None]
        elif has_due_date is False:
            tasks = [t for t in tasks if t.due_date is None]
        return tasks
