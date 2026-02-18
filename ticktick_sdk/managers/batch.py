"""Batch sync operations - the core TickTick sync mechanism."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class BatchManager:
    """Batch sync: the primary mechanism TickTick uses to sync data.

    The batch/check endpoint returns all user data (tasks, projects, tags,
    filters, etc.) that has changed since the last checkpoint.
    """

    def __init__(self, client: TickTickClient):
        self._c = client
        self._checkpoint: int = 0

    def check(self, checkpoint: int | None = None) -> dict:
        """Fetch all data since the given checkpoint.

        Args:
            checkpoint: Sync checkpoint timestamp. 0 returns everything.
                       None uses the last stored checkpoint.

        Returns:
            Full sync response with keys:
                - checkPoint: New checkpoint for next sync
                - syncTaskBean: {update, tagUpdate, delete, add, empty}
                - projectProfiles: List of project dicts
                - projectGroups: List of project group dicts
                - filters: List of filter dicts
                - tags: List of tag dicts
                - syncTaskOrderBean: Task ordering data
                - inboxId: Inbox project ID
                - remindChanges: Reminder changes
        """
        cp = checkpoint if checkpoint is not None else self._checkpoint
        resp = self._c.get(f"/api/v3/batch/check/{cp}")
        data = resp.json()
        new_cp = data.get("checkPoint", self._checkpoint)
        self._checkpoint = new_cp
        if "inboxId" in data and data["inboxId"]:
            self._c.inbox_id = data["inboxId"]
        return data

    def full_sync(self) -> dict:
        """Perform a full sync from scratch (checkpoint=0)."""
        self._checkpoint = 0
        return self.check(0)

    def delta_sync(self) -> dict:
        """Perform an incremental sync using the last checkpoint."""
        return self.check()

    @property
    def checkpoint(self) -> int:
        return self._checkpoint

    @checkpoint.setter
    def checkpoint(self, value: int) -> None:
        self._checkpoint = value
