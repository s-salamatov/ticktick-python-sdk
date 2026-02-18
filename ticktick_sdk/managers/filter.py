"""Filter management - CRUD for saved filters / smart lists."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ticktick_sdk.models import Filter

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class FilterManager:
    """Manage saved filters (smart lists) with rule-based criteria."""

    def __init__(self, client: TickTickClient):
        self._c = client

    # ── Read ──────────────────────────────────────────────────────────

    def get_all(self) -> list[Filter]:
        """Get all saved filters via full sync (checkpoint=0).

        Delta sync may omit unchanged filters, so a full sync is used.
        """
        data = self._c.batch.check(0)
        return [Filter.from_dict(f) for f in data.get("filters") or []]

    def get(self, filter_id: str) -> Filter | None:
        """Get a filter by ID."""
        for f in self.get_all():
            if f.id == filter_id:
                return f
        return None

    # ── Create ────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        rule: dict | str,
        *,
        sort_type: str = "sortOrder",
        view_mode: str = "list",
        sort_order: int = 0,
    ) -> dict:
        """Create a saved filter (smart list).

        Args:
            name: Filter display name.
            rule: Filter rule as dict or JSON string. See build_rule() for helpers.
            sort_type: Sort type for results ("sortOrder", "priority", "dueDate", etc).
            view_mode: "list", "kanban", or "timeline".
            sort_order: Sort position in sidebar.

        Returns:
            Raw API response dict.
        """
        rule_str = json.dumps(rule) if isinstance(rule, dict) else rule
        payload = {
            "name": name,
            "rule": rule_str,
            "sortType": sort_type,
            "sortOrder": sort_order,
            "viewMode": view_mode,
        }
        resp = self._c.post("/api/v2/batch/filter", json={"add": [payload]})
        batch_resp = resp.json()
        # Batch returns {"id2etag": {"<id>": "<etag>"}, "id2error": {}}.
        # Extract the created filter ID and fetch full object via sync.
        id2etag = batch_resp.get("id2etag", {})
        if id2etag:
            filt_id = next(iter(id2etag))
            data = self._c.batch.full_sync()
            for f in data.get("filters") or []:
                if f.get("id") == filt_id:
                    return f
            return {"id": filt_id, **payload}
        return batch_resp

    # ── Update ────────────────────────────────────────────────────────

    def update(self, filter_obj: Filter) -> dict:
        """Update a filter."""
        payload = filter_obj.to_dict()
        return self._c.post("/api/v2/batch/filter", json={"update": [payload]}).json()

    # ── Delete ────────────────────────────────────────────────────────

    def delete(self, filter_id: str) -> None:
        """Delete a saved filter."""
        self._c.post("/api/v2/batch/filter", json={"delete": [filter_id]})

    # ── Rule helpers ──────────────────────────────────────────────────

    @staticmethod
    def build_rule(
        *,
        project_ids: list[str] | None = None,
        tag_names: list[str] | None = None,
        priority: list[int] | None = None,
        status: str | None = None,
        task_type: str = "task",
    ) -> dict:
        """Build a filter rule dict.

        Args:
            project_ids: Filter to specific project IDs.
            tag_names: Filter by tag names.
            priority: Filter by priority levels (0, 1, 3, 5).
            status: "completed", "uncompleted", or None for all.
            task_type: "task" or "note".

        Returns:
            A rule dict suitable for create().

        Example:
            rule = FilterManager.build_rule(
                project_ids=["abc123"],
                priority=[5, 3],
            )
            client.filter.create("High Priority Tasks", rule)
        """
        conditions = []

        if project_ids:
            conditions.append(
                {
                    "conditionType": 1,
                    "or": [{"or": project_ids, "conditionName": "list"}],
                    "conditionName": "listOrGroup",
                }
            )

        if tag_names:
            conditions.append(
                {
                    "conditionType": 1,
                    "or": tag_names,
                    "conditionName": "tag",
                }
            )

        if priority is not None:
            conditions.append(
                {
                    "conditionType": 1,
                    "or": [str(p) for p in priority],
                    "conditionName": "priority",
                }
            )

        if status:
            conditions.append(
                {
                    "conditionType": 1,
                    "or": [status],
                    "conditionName": "status",
                }
            )

        conditions.append(
            {
                "conditionType": 1,
                "or": [task_type],
                "conditionName": "taskType",
            }
        )

        return {"type": 0, "and": conditions, "version": 3}
