"""Column (section) management for Kanban boards."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ticktick_sdk.models import Column

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class ColumnManager:
    """Manage Kanban columns / sections within projects."""

    def __init__(self, client: TickTickClient):
        self._c = client

    # ── Read ──────────────────────────────────────────────────────────

    def get_all(self, since: int = 0) -> list[Column]:
        """Get all columns across all projects.

        Args:
            since: Timestamp to get columns modified since. 0 = all.
        """
        resp = self._c.get("/api/v2/column", params={"from": since})
        data = resp.json()
        columns = data if isinstance(data, list) else data.get("columns", [])
        return [Column.from_dict(c) for c in columns]

    def get_by_project(self, project_id: str) -> list[Column]:
        """Get all columns/sections for a specific project."""
        resp = self._c.get(f"/api/v2/column/project/{project_id}")
        data = resp.json()
        columns = data if isinstance(data, list) else data.get("columns", [])
        return [Column.from_dict(c) for c in columns]

    # ── Create ────────────────────────────────────────────────────────

    def create(
        self,
        project_id: str,
        name: str,
        *,
        sort_order: int = 0,
    ) -> Column:
        """Create a new column/section in a project.

        Args:
            project_id: The project to add the column to.
            name: Column display name.
            sort_order: Sort position.
        """
        column_id = os.urandom(12).hex()
        payload = {
            "id": column_id,
            "projectId": project_id,
            "name": name,
            "sortOrder": sort_order,
        }
        self._c.post("/api/v2/column", json=payload)
        # The endpoint returns {"id2etag": ..., "id2error": ...} rather than
        # the column object.  Fetch columns for the project and return ours.
        for col in self.get_by_project(project_id):
            if col.id == column_id:
                return col
        # Fallback: construct locally if the API didn't persist it.
        return Column(id=column_id, project_id=project_id, name=name, sort_order=sort_order)

    # ── Update ────────────────────────────────────────────────────────

    def update(self, column: Column) -> Column:
        """Update a column.

        Uses the same POST endpoint as create — the API identifies
        existing columns by ``id`` and applies the update.
        """
        self._c.post("/api/v2/column", json=column.to_dict())
        for c in self.get_by_project(column.project_id):
            if c.id == column.id:
                return c
        return column

    def rename(self, column_id: str, project_id: str, new_name: str) -> Column:
        """Rename a column/section."""
        columns = self.get_by_project(project_id)
        for col in columns:
            if col.id == column_id:
                col.name = new_name
                return self.update(col)
        raise ValueError(f"Column {column_id} not found in project {project_id}")

    # ── Delete ────────────────────────────────────────────────────────

    def delete(self, column_id: str, project_id: str) -> None:
        """Delete a column/section.

        Note: The TickTick web API does not expose a standalone column
        delete endpoint.  Deleting the parent *project* removes all its
        columns.  This method is kept for interface symmetry but raises
        ``NotImplementedError`` until a working endpoint is discovered.
        """
        raise NotImplementedError(
            "The TickTick API does not support standalone column deletion. "
            "Delete the parent project to remove its columns."
        )
