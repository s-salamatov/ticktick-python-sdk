"""Tag management - CRUD for tags and sub-tags."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from ticktick_sdk.models import Tag, Task

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class TagManager:
    """Manage tags, sub-tags (hierarchical), and tag-based queries."""

    def __init__(self, client: TickTickClient):
        self._c = client

    # ── Read ──────────────────────────────────────────────────────────

    def get_all(self) -> list[Tag]:
        """Get all tags via full sync (checkpoint=0).

        Delta sync may omit unchanged tags, so a full sync is used.
        """
        data = self._c.batch.check(0)
        return [Tag.from_dict(t) for t in data.get("tags") or []]

    def get(self, tag_name: str) -> Tag | None:
        """Get a tag by name."""
        tags = self.get_all()
        for t in tags:
            if t.name == tag_name:
                return t
        return None

    def get_children(self, parent_name: str) -> list[Tag]:
        """Get sub-tags of a parent tag.

        Tags are hierarchical via naming convention: "parent/child".
        """
        tags = self.get_all()
        return [t for t in tags if t.parent == parent_name]

    def get_completed_tasks(
        self,
        tag_names: list[str],
        *,
        limit: int = 50,
        token: str = "",
    ) -> list[Task]:
        """Get completed tasks for given tag names (paginated).

        Args:
            tag_names: List of tag names to filter by.
            limit: Max results per page.
            token: Pagination token from previous response.
        """
        resp = self._c.post("/api/v2/tag/completedTask", json={
            "tags": tag_names,
            "token": token,
            "limit": limit,
        })
        return [Task.from_dict(t) for t in resp.json()]

    # ── Create ────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        *,
        label: str = "",
        color: str = "",
        sort_order: int = 0,
        sort_type: str = "",
        parent: str = "",
    ) -> Tag:
        """Create a new tag.

        Args:
            name: Tag name. For sub-tags, use "parent/child" format.
            label: Display label.
            color: Hex color code.
            sort_order: Sort position.
            sort_type: Sort type for tasks in this tag view.
            parent: Parent tag name (alternative to using "/" in name).
        """
        if parent and "/" not in name:
            name = f"{parent}/{name}"
        payload: dict[str, Any] = {
            "name": name,
            "label": label or name,
            "sortOrder": sort_order,
            "color": color,
        }
        if sort_type:
            payload["sortType"] = sort_type
        self._c.post("/api/v2/batch/tag", json={"add": [payload]})
        # Batch endpoint returns id2etag, not the tag object; fetch via sync.
        data = self._c.batch.full_sync()
        for t in data.get("tags") or []:
            if t.get("name", "").lower() == name.lower():
                return Tag.from_dict(t)
        return Tag(name=name, label=label or name, color=color, sort_order=sort_order)

    # ── Update ────────────────────────────────────────────────────────

    def rename(self, old_name: str, new_name: str) -> dict:
        """Rename a tag across all tasks."""
        return self._c.put("/api/v2/tag/rename", json={
            "name": old_name,
            "newName": new_name,
        }).json()

    def update(self, tag: Tag) -> dict:
        """Update tag properties (color, sort, etc)."""
        return self._c.post("/api/v2/batch/tag", json={"update": [tag.to_dict()]}).json()

    # ── Delete ────────────────────────────────────────────────────────

    def delete(self, tag_name: str) -> None:
        """Delete a tag. Removes the tag from all tasks."""
        if "/" in tag_name:
            # Sub-tag names contain '/' which breaks both direct DELETE
            # (path confusion) and percent-encoded DELETE (400 error).
            # Use the batch endpoint instead.
            self._c.post("/api/v2/batch/tag", json={"delete": [tag_name]})
        else:
            self._c.delete(f"/api/v2/tag/{quote(tag_name, safe='')}")

    # ── Sub-tag helpers ───────────────────────────────────────────────

    def create_subtag(self, parent_name: str, child_name: str, **kwargs: Any) -> Tag:
        """Create a sub-tag under a parent tag.

        This creates a tag named "parent_name/child_name".
        """
        return self.create(f"{parent_name}/{child_name}", **kwargs)
