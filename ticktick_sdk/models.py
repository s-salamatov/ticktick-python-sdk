"""Data models for TickTick API objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _format_dt(dt: datetime) -> str:
    """Format a datetime for the TickTick API (UTC, millisecond precision)."""
    utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt
    return utc.strftime("%Y-%m-%dT%H:%M:%S.000+0000")


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


@dataclass
class Subtask:
    id: str
    title: str
    status: int = 0  # 0=open, 2=completed
    sort_order: int = 0
    start_date: datetime | None = None
    is_all_day: bool = False
    time_zone: str = ""
    completed_time: datetime | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Subtask:
        return cls(
            id=d["id"],
            title=d.get("title", ""),
            status=d.get("status", 0),
            sort_order=d.get("sortOrder", 0),
            start_date=_parse_dt(d.get("startDate")),
            is_all_day=d.get("isAllDay", False),
            time_zone=d.get("timeZone", ""),
            completed_time=_parse_dt(d.get("completedTime")),
        )

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"id": self.id, "title": self.title, "status": self.status, "sortOrder": self.sort_order}
        if self.start_date:
            d["startDate"] = _format_dt(self.start_date)
        d["isAllDay"] = self.is_all_day
        if self.time_zone:
            d["timeZone"] = self.time_zone
        if self.completed_time:
            d["completedTime"] = _format_dt(self.completed_time)
        return d


@dataclass
class Reminder:
    id: str
    trigger: str  # iCal TRIGGER format, e.g. "TRIGGER:P0DT9H0M0S"

    @classmethod
    def from_dict(cls, d: dict) -> Reminder:
        return cls(id=d["id"], trigger=d.get("trigger", ""))

    def to_dict(self) -> dict:
        return {"id": self.id, "trigger": self.trigger}


@dataclass
class Task:
    id: str
    project_id: str
    title: str
    content: str = ""
    desc: str = ""
    priority: int = 0  # 0=none, 1=low, 3=medium, 5=high
    status: int = 0  # 0=open, 2=completed
    tags: list[str] = field(default_factory=list)
    items: list[Subtask] = field(default_factory=list)
    reminders: list[Reminder] = field(default_factory=list)
    start_date: datetime | None = None
    due_date: datetime | None = None
    is_all_day: bool = False
    is_floating: bool = False
    time_zone: str = ""
    repeat_flag: str = ""  # iCal RRULE, e.g. "RRULE:FREQ=DAILY;INTERVAL=1"
    repeat_from: str = ""
    sort_order: int = 0
    progress: int = 0
    kind: str = "TEXT"  # TEXT or NOTE
    parent_id: str = ""
    column_id: str = ""
    etag: str = ""
    deleted: int = 0
    created_time: datetime | None = None
    modified_time: datetime | None = None
    creator: int = 0
    comment_count: int = 0
    attachments: list[dict] = field(default_factory=list)
    child_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> Task:
        items = [Subtask.from_dict(i) for i in d.get("items", []) or []]
        reminders = [Reminder.from_dict(r) for r in d.get("reminders", []) or []]
        return cls(
            id=d["id"],
            project_id=d.get("projectId", ""),
            title=d.get("title", ""),
            content=d.get("content", ""),
            desc=d.get("desc", ""),
            priority=d.get("priority", 0),
            status=d.get("status", 0),
            tags=d.get("tags") or [],
            items=items,
            reminders=reminders,
            start_date=_parse_dt(d.get("startDate")),
            due_date=_parse_dt(d.get("dueDate")),
            is_all_day=d.get("isAllDay", False),
            is_floating=d.get("isFloating", False),
            time_zone=d.get("timeZone", ""),
            repeat_flag=d.get("repeatFlag", "") or "",
            repeat_from=d.get("repeatFrom", "") or "",
            sort_order=d.get("sortOrder", 0),
            progress=d.get("progress", 0),
            kind=d.get("kind", "TEXT"),
            parent_id=d.get("parentId", "") or "",
            column_id=d.get("columnId", "") or "",
            etag=d.get("etag", ""),
            deleted=d.get("deleted", 0),
            created_time=_parse_dt(d.get("createdTime")),
            modified_time=_parse_dt(d.get("modifiedTime")),
            creator=d.get("creator", 0),
            comment_count=d.get("commentCount", 0),
            attachments=d.get("attachments") or [],
            child_ids=d.get("childIds") or [],
        )

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "projectId": self.project_id,
            "title": self.title,
            "content": self.content,
            "desc": self.desc,
            "priority": self.priority,
            "status": self.status,
            "isAllDay": self.is_all_day,
            "isFloating": self.is_floating,
            "kind": self.kind,
            "sortOrder": self.sort_order,
            "items": [i.to_dict() for i in self.items],
            "reminders": [r.to_dict() for r in self.reminders],
            "tags": self.tags,
            "progress": self.progress,
        }
        if self.time_zone:
            d["timeZone"] = self.time_zone
        if self.start_date:
            d["startDate"] = _format_dt(self.start_date)
        if self.due_date:
            d["dueDate"] = _format_dt(self.due_date)
        if self.repeat_flag:
            d["repeatFlag"] = self.repeat_flag
        if self.repeat_from:
            d["repeatFrom"] = self.repeat_from
        if self.parent_id:
            d["parentId"] = self.parent_id
        if self.column_id:
            d["columnId"] = self.column_id
        if self.etag:
            d["etag"] = self.etag
        if self.attachments:
            d["attachments"] = self.attachments
        if self.child_ids:
            d["childIds"] = self.child_ids
        return d


@dataclass
class SortOption:
    group_by: str = "sortOrder"
    order_by: str = "sortOrder"
    order: str | None = None

    @classmethod
    def from_dict(cls, d: dict | None) -> SortOption:
        if not d:
            return cls()
        return cls(
            group_by=d.get("groupBy", "sortOrder"),
            order_by=d.get("orderBy", "sortOrder"),
            order=d.get("order"),
        )

    def to_dict(self) -> dict:
        return {"groupBy": self.group_by, "orderBy": self.order_by, "order": self.order}


@dataclass
class Project:
    id: str
    name: str
    is_owner: bool = True
    color: str | None = None
    sort_order: int = 0
    sort_type: str = "sortOrder"
    sort_option: SortOption = field(default_factory=SortOption)
    user_count: int = 1
    etag: str = ""
    modified_time: datetime | None = None
    in_all: bool = True
    show_type: int = 0
    muted: bool = False
    closed: bool | None = None
    group_id: str | None = None
    view_mode: str = "list"  # list, kanban, timeline
    kind: str = "TASK"
    team_id: str | None = None
    source: int = 0
    background: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Project:
        return cls(
            id=d["id"],
            name=d.get("name", ""),
            is_owner=d.get("isOwner", True),
            color=d.get("color"),
            sort_order=d.get("sortOrder", 0),
            sort_type=d.get("sortType", "sortOrder"),
            sort_option=SortOption.from_dict(d.get("sortOption")),
            user_count=d.get("userCount", 1),
            etag=d.get("etag", ""),
            modified_time=_parse_dt(d.get("modifiedTime")),
            in_all=d.get("inAll", True),
            show_type=d.get("showType", 0),
            muted=d.get("muted", False),
            closed=d.get("closed"),
            group_id=d.get("groupId"),
            view_mode=d.get("viewMode", "list"),
            kind=d.get("kind", "TASK"),
            team_id=d.get("teamId"),
            source=d.get("source", 0),
            background=d.get("background"),
        )

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "sortOrder": self.sort_order,
            "sortType": self.sort_type,
            "sortOption": self.sort_option.to_dict(),
            "viewMode": self.view_mode,
            "kind": self.kind,
            "inAll": self.in_all,
        }
        if self.color:
            d["color"] = self.color
        if self.group_id:
            d["groupId"] = self.group_id
        if self.closed is not None:
            d["closed"] = self.closed
        return d


@dataclass
class ProjectGroup:
    id: str
    name: str
    show_all: bool = True
    sort_order: int = 0
    view_mode: str | None = None
    sort_type: str | None = None
    etag: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> ProjectGroup:
        return cls(
            id=d["id"],
            name=d.get("name", ""),
            show_all=d.get("showAll", True),
            sort_order=d.get("sortOrder", 0),
            view_mode=d.get("viewMode"),
            sort_type=d.get("sortType"),
            etag=d.get("etag", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "showAll": self.show_all,
            "sortOrder": self.sort_order,
        }


@dataclass
class Tag:
    name: str
    raw_name: str = ""
    label: str = ""
    sort_order: int = 0
    sort_type: str = ""
    color: str = ""
    etag: str = ""
    type: int = 0
    parent: str = ""  # parent tag name for sub-tags (name is "parent/child")
    sort_option: SortOption = field(default_factory=SortOption)

    @classmethod
    def from_dict(cls, d: dict) -> Tag:
        name = d.get("name", "")
        parent = ""
        if "/" in name:
            parts = name.rsplit("/", 1)
            parent = parts[0]
        return cls(
            name=name,
            raw_name=d.get("rawName", ""),
            label=d.get("label", ""),
            sort_order=d.get("sortOrder", 0),
            sort_type=d.get("sortType", ""),
            color=d.get("color", ""),
            etag=d.get("etag", ""),
            type=d.get("type", 0),
            parent=parent,
            sort_option=SortOption.from_dict(d.get("sortOption")),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "sortOrder": self.sort_order,
            "sortType": self.sort_type,
            "color": self.color,
        }


@dataclass
class Filter:
    id: str
    name: str
    rule: str = ""  # JSON string defining filter criteria
    sort_order: int = 0
    sort_type: str = ""
    view_mode: str = "list"
    etag: str = ""
    created_time: datetime | None = None
    modified_time: datetime | None = None
    sort_option: SortOption = field(default_factory=SortOption)

    @classmethod
    def from_dict(cls, d: dict) -> Filter:
        return cls(
            id=d["id"],
            name=d.get("name", ""),
            rule=d.get("rule", ""),
            sort_order=d.get("sortOrder", 0),
            sort_type=d.get("sortType", ""),
            view_mode=d.get("viewMode", "list"),
            etag=d.get("etag", ""),
            created_time=_parse_dt(d.get("createdTime")),
            modified_time=_parse_dt(d.get("modifiedTime")),
            sort_option=SortOption.from_dict(d.get("sortOption")),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "rule": self.rule,
            "sortOrder": self.sort_order,
            "sortType": self.sort_type,
            "viewMode": self.view_mode,
        }


@dataclass
class Habit:
    id: str
    name: str
    icon_res: str = ""
    color: str = ""
    sort_order: int = 0
    status: int = 0  # 0=active, 1=archived, 2=deleted
    encouragement: str = ""
    total_check_ins: int = 0
    type: str = "Boolean"  # Boolean or Real
    goal: int | float = 1
    step: int | float = 1
    unit: str = "Count"
    repeat_rule: str = ""  # iCal RRULE
    reminders: list[dict] = field(default_factory=list)
    record_enable: bool = False
    section_id: str = ""
    target_days: int = 0
    target_start_date: int = 0  # YYYYMMDD format
    completed_cycles: int = 0
    created_time: datetime | None = None
    modified_time: datetime | None = None
    archived_time: datetime | None = None
    etag: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Habit:
        return cls(
            id=d["id"],
            name=d.get("name", ""),
            icon_res=d.get("iconRes", ""),
            color=d.get("color", ""),
            sort_order=d.get("sortOrder", 0),
            status=d.get("status", 0),
            encouragement=d.get("encouragement", "") or "",
            total_check_ins=d.get("totalCheckIns", 0),
            type=d.get("type", "Boolean"),
            goal=d.get("goal", 1),
            step=d.get("step", 1),
            unit=d.get("unit", "Count"),
            repeat_rule=d.get("repeatRule", ""),
            reminders=d.get("reminders") or [],
            record_enable=d.get("recordEnable", False),
            section_id=d.get("sectionId", ""),
            target_days=d.get("targetDays", 0),
            target_start_date=d.get("targetStartDate", 0),
            completed_cycles=d.get("completedCycles", 0),
            created_time=_parse_dt(d.get("createdTime")),
            modified_time=_parse_dt(d.get("modifiedTime")),
            archived_time=_parse_dt(d.get("archivedTime")),
            etag=d.get("etag", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "iconRes": self.icon_res,
            "color": self.color,
            "sortOrder": self.sort_order,
            "status": self.status,
            "encouragement": self.encouragement,
            "type": self.type,
            "goal": self.goal,
            "step": self.step,
            "unit": self.unit,
            "repeatRule": self.repeat_rule,
            "reminders": self.reminders,
            "recordEnable": self.record_enable,
            "sectionId": self.section_id,
            "targetDays": self.target_days,
            "targetStartDate": self.target_start_date,
        }


@dataclass
class HabitCheckin:
    id: str
    habit_id: str
    status: int = 0
    value: float = 0
    checkin_stamp: str = ""  # YYYYMMDD format
    checkin_time: datetime | None = None
    goal: float = 1
    etag: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> HabitCheckin:
        return cls(
            id=d.get("id", ""),
            habit_id=d.get("habitId", ""),
            status=d.get("status", 0),
            value=d.get("value", 0),
            checkin_stamp=d.get("checkinStamp", ""),
            checkin_time=_parse_dt(d.get("checkinTime")),
            goal=d.get("goal", 1),
            etag=d.get("etag", ""),
        )

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "habitId": self.habit_id,
            "status": self.status,
            "value": self.value,
            "checkinStamp": self.checkin_stamp,
        }
        if self.goal:
            d["goal"] = self.goal
        if self.checkin_time:
            d["checkinTime"] = _format_dt(self.checkin_time)
        return d


@dataclass
class Column:
    """Kanban column (section within a project)."""

    id: str
    project_id: str
    name: str
    sort_order: int = 0
    etag: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Column:
        return cls(
            id=d["id"],
            project_id=d.get("projectId", ""),
            name=d.get("name", ""),
            sort_order=d.get("sortOrder", 0),
            etag=d.get("etag", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "projectId": self.project_id,
            "name": self.name,
            "sortOrder": self.sort_order,
        }
