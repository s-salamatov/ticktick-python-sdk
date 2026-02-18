"""Habit management - CRUD for habits and check-ins."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from ticktick_sdk.models import Habit, HabitCheckin

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class HabitManager:
    """Manage habits, check-ins, sections, and archival."""

    def __init__(self, client: TickTickClient):
        self._c = client

    # ── Read ──────────────────────────────────────────────────────────

    def get_all(self) -> list[Habit]:
        """Get all habits (active and archived)."""
        resp = self._c.get("/api/v2/habits")
        return [Habit.from_dict(h) for h in resp.json()]

    def get_active(self) -> list[Habit]:
        """Get only active (non-archived) habits."""
        return [h for h in self.get_all() if h.status == 0]

    def get_archived(self) -> list[Habit]:
        """Get only archived habits."""
        return [h for h in self.get_all() if h.status == 1]

    def get(self, habit_id: str) -> Habit | None:
        """Get a habit by ID."""
        for h in self.get_all():
            if h.id == habit_id:
                return h
        return None

    def get_checkins(
        self,
        habit_ids: list[str] | None = None,
        *,
        after_stamp: str = "",
    ) -> list[HabitCheckin]:
        """Query habit check-in records.

        Args:
            habit_ids: Filter to specific habit IDs. None returns all.
            after_stamp: Return checkins after this date stamp (YYYYMMDD).
        """
        payload: dict[str, Any] = {}
        if habit_ids:
            payload["habitIds"] = habit_ids
        if after_stamp:
            payload["afterStamp"] = after_stamp
        resp = self._c.post("/api/v2/habitCheckins/query", json=payload)
        data = resp.json()
        # Response can be:
        #   - a flat list of checkin dicts, OR
        #   - {"checkins": {habit_id: [checkin, ...], ...}}
        if isinstance(data, list):
            return [HabitCheckin.from_dict(c) for c in data]
        raw = data.get("checkins", {})
        if isinstance(raw, dict):
            flat = [c for per_habit in raw.values() for c in per_habit]
            return [HabitCheckin.from_dict(c) for c in flat]
        return [HabitCheckin.from_dict(c) for c in raw]

    def get_preferences(self) -> dict:
        """Get habit preferences (calendar/today visibility, etc)."""
        return self._c.get("/api/v2/user/preferences/habit", params={"platform": "web"}).json()

    # ── Create ────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        *,
        icon_res: str = "habit_daily_check_in",
        color: str = "#7BC4FA",
        type: str = "Boolean",
        goal: int | float = 1,
        step: int | float = 1,
        unit: str = "Count",
        repeat_rule: str = "RRULE:FREQ=DAILY;INTERVAL=1",
        encouragement: str = "",
        section_id: str = "-1",
        target_days: int = 0,
        target_start_date: int = 0,
        reminders: list[dict] | None = None,
    ) -> Habit:
        """Create a new habit.

        Args:
            name: Habit name.
            icon_res: Icon resource name (e.g. "habit_reading", "habit_exercise").
            color: Hex color code.
            type: "Boolean" (yes/no) or "Real" (numeric tracking).
            goal: Target value per check-in (1 for Boolean).
            step: Increment step for Real type habits.
            unit: Unit of measurement ("Count", "Minute", "ml", etc).
            repeat_rule: iCal RRULE for repeat schedule.
            encouragement: Motivational message.
            section_id: Section ID for grouping ("-1" for unsectioned).
            target_days: Target streak days (0 for unlimited).
            target_start_date: Start date as YYYYMMDD int.
            reminders: List of reminder dicts.
        """
        payload: dict[str, Any] = {
            "name": name,
            "iconRes": icon_res,
            "color": color,
            "type": type,
            "goal": goal,
            "step": step,
            "unit": unit,
            "repeatRule": repeat_rule,
            "encouragement": encouragement,
            "sectionId": section_id,
            "targetDays": target_days,
            "targetStartDate": target_start_date or int(date.today().strftime("%Y%m%d")),
            "reminders": reminders or [],
            "recordEnable": False,
            "status": 0,
        }
        resp = self._c.post("/api/v2/habits", json=payload)
        return Habit.from_dict(resp.json())

    # ── Update ────────────────────────────────────────────────────────

    def update(self, habit: Habit) -> Habit:
        """Update a habit."""
        resp = self._c.put(f"/api/v2/habits/{habit.id}", json=habit.to_dict())
        return Habit.from_dict(resp.json())

    def archive(self, habit_id: str) -> Habit:
        """Archive a habit."""
        habit = self.get(habit_id)
        if not habit:
            raise ValueError(f"Habit {habit_id} not found")
        habit.status = 1
        return self.update(habit)

    def unarchive(self, habit_id: str) -> Habit:
        """Unarchive a habit."""
        habit = self.get(habit_id)
        if not habit:
            raise ValueError(f"Habit {habit_id} not found")
        habit.status = 0
        return self.update(habit)

    # ── Delete ────────────────────────────────────────────────────────

    def delete(self, habit_id: str) -> None:
        """Delete a habit permanently."""
        self._c.delete(f"/api/v2/habits/{habit_id}")

    # ── Check-ins ─────────────────────────────────────────────────────

    def checkin(
        self,
        habit_id: str,
        *,
        stamp: str = "",
        value: float = 1,
        status: int = 2,
    ) -> HabitCheckin:
        """Record a habit check-in.

        Args:
            habit_id: The habit to check in.
            stamp: Date stamp as YYYYMMDD string. Defaults to today.
            value: Value to record (1 for Boolean habits, numeric for Real).
            status: Check-in status (0=unchecked, 2=checked).
        """
        if not stamp:
            stamp = date.today().strftime("%Y%m%d")
        payload = {
            "habitId": habit_id,
            "checkinStamp": stamp,
            "value": value,
            "status": status,
        }
        resp = self._c.post("/api/v2/habitCheckins", json=payload)
        return HabitCheckin.from_dict(resp.json())

    def batch_checkin(self, checkins: list[dict[str, Any]]) -> list[dict]:
        """Batch check-in for multiple habits.

        Args:
            checkins: List of check-in dicts with habitId, checkinStamp, value, status.
        """
        return self._c.post("/api/v2/habits/batch", json={"checkins": checkins}).json()
