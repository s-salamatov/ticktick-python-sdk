"""Unit tests for ticktick_sdk.models."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta


from ticktick_sdk.models import (
    _format_dt,
    _parse_dt,
    Task,
    Subtask,
    Reminder,
    Project,
    ProjectGroup,
    Tag,
    Filter,
    Habit,
    HabitCheckin,
    Column,
    SortOption,
)


# ---------------------------------------------------------------------------
# _format_dt / _parse_dt
# ---------------------------------------------------------------------------


def test_format_dt_naive():
    """Naive datetimes are used as-is (no tz conversion)."""
    dt = datetime(2024, 3, 15, 10, 30, 0)
    result = _format_dt(dt)
    assert result == "2024-03-15T10:30:00.000+0000"


def test_format_dt_utc_aware():
    """UTC-aware datetimes are formatted correctly."""
    dt = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc)
    result = _format_dt(dt)
    assert result == "2024-03-15T10:30:00.000+0000"


def test_format_dt_offset_aware():
    """Offset-aware datetimes are converted to UTC before formatting."""
    # UTC+5 -> subtract 5h to get UTC
    tz_plus5 = timezone(timedelta(hours=5))
    dt = datetime(2024, 3, 15, 15, 30, 0, tzinfo=tz_plus5)
    result = _format_dt(dt)
    assert result == "2024-03-15T10:30:00.000+0000"


def test_parse_dt_with_milliseconds_and_tz():
    """Parse TickTick's primary datetime format."""
    val = "2024-03-15T10:30:00.000+0000"
    result = _parse_dt(val)
    assert result is not None
    assert result.year == 2024
    assert result.month == 3
    assert result.day == 15
    assert result.hour == 10
    assert result.minute == 30


def test_parse_dt_without_milliseconds():
    """Parse datetimes without fractional seconds."""
    val = "2024-03-15T10:30:00+0000"
    result = _parse_dt(val)
    assert result is not None
    assert result.hour == 10


def test_parse_dt_no_tz():
    """Parse datetimes with no timezone (space-separated format)."""
    val = "2024-03-15 10:30:00"
    result = _parse_dt(val)
    assert result is not None
    assert result.year == 2024
    assert result.minute == 30


def test_parse_dt_none():
    assert _parse_dt(None) is None


def test_parse_dt_empty_string():
    assert _parse_dt("") is None


def test_parse_dt_invalid():
    """Unrecognised format returns None."""
    assert _parse_dt("not-a-date") is None


# ---------------------------------------------------------------------------
# Subtask
# ---------------------------------------------------------------------------

SUBTASK_DICT = {
    "id": "sub123",
    "title": "Write tests",
    "status": 0,
    "sortOrder": 1099511627776,
    "startDate": "2024-03-15T09:00:00.000+0000",
    "isAllDay": False,
    "timeZone": "America/New_York",
    "completedTime": None,
}


def test_subtask_from_dict():
    st = Subtask.from_dict(SUBTASK_DICT)
    assert st.id == "sub123"
    assert st.title == "Write tests"
    assert st.status == 0
    assert st.sort_order == 1099511627776
    assert st.start_date is not None
    assert st.start_date.hour == 9
    assert st.is_all_day is False
    assert st.time_zone == "America/New_York"
    assert st.completed_time is None


def test_subtask_from_dict_minimal():
    """Only 'id' is required; everything else is defaulted."""
    st = Subtask.from_dict({"id": "x"})
    assert st.id == "x"
    assert st.title == ""
    assert st.status == 0
    assert st.sort_order == 0
    assert st.is_all_day is False
    assert st.start_date is None
    assert st.completed_time is None


def test_subtask_to_dict_no_completed_time():
    st = Subtask.from_dict(SUBTASK_DICT)
    d = st.to_dict()
    assert d["id"] == "sub123"
    assert d["title"] == "Write tests"
    assert d["status"] == 0
    assert d["sortOrder"] == 1099511627776
    assert "startDate" in d
    assert d["isAllDay"] is False
    assert d["timeZone"] == "America/New_York"
    assert "completedTime" not in d  # None -> omitted


def test_subtask_to_dict_includes_completed_time():
    st = Subtask.from_dict(
        {
            **SUBTASK_DICT,
            "completedTime": "2024-03-15T12:00:00.000+0000",
        }
    )
    d = st.to_dict()
    assert "completedTime" in d
    assert "2024-03-15" in d["completedTime"]


def test_subtask_round_trip():
    st = Subtask.from_dict(SUBTASK_DICT)
    d = st.to_dict()
    st2 = Subtask.from_dict(d)
    assert st2.id == st.id
    assert st2.title == st.title
    assert st2.sort_order == st.sort_order
    assert st2.time_zone == st.time_zone


# ---------------------------------------------------------------------------
# Reminder
# ---------------------------------------------------------------------------


def test_reminder_from_dict():
    r = Reminder.from_dict({"id": "rem1", "trigger": "TRIGGER:P0DT9H0M0S"})
    assert r.id == "rem1"
    assert r.trigger == "TRIGGER:P0DT9H0M0S"


def test_reminder_to_dict():
    r = Reminder(id="rem1", trigger="TRIGGER:P0DT9H0M0S")
    d = r.to_dict()
    assert d == {"id": "rem1", "trigger": "TRIGGER:P0DT9H0M0S"}


def test_reminder_round_trip():
    raw = {"id": "rem1", "trigger": "TRIGGER:P0DT9H0M0S"}
    r = Reminder.from_dict(raw)
    assert r.to_dict() == raw


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

TASK_DICT = {
    "id": "task001",
    "projectId": "proj001",
    "title": "Buy groceries",
    "content": "- Milk\n- Eggs",
    "desc": "shopping list",
    "priority": 3,
    "status": 0,
    "tags": ["personal", "errands"],
    "items": [
        {
            "id": "sub001",
            "title": "Get milk",
            "status": 0,
            "sortOrder": 0,
            "isAllDay": False,
        }
    ],
    "reminders": [{"id": "rem001", "trigger": "TRIGGER:P0DT9H0M0S"}],
    "startDate": "2024-03-15T09:00:00.000+0000",
    "dueDate": "2024-03-15T18:00:00.000+0000",
    "isAllDay": False,
    "isFloating": False,
    "timeZone": "America/New_York",
    "repeatFlag": "RRULE:FREQ=WEEKLY;INTERVAL=1",
    "repeatFrom": "1",
    "sortOrder": 5000,
    "progress": 0,
    "kind": "TEXT",
    "parentId": "",
    "columnId": "",
    "etag": "abc123etag",
    "deleted": 0,
    "createdTime": "2024-03-01T08:00:00.000+0000",
    "modifiedTime": "2024-03-10T10:00:00.000+0000",
    "creator": 9999,
    "commentCount": 2,
    "attachments": [],
    "childIds": [],
}


def test_task_from_dict():
    task = Task.from_dict(TASK_DICT)
    assert task.id == "task001"
    assert task.project_id == "proj001"
    assert task.title == "Buy groceries"
    assert task.content == "- Milk\n- Eggs"
    assert task.priority == 3
    assert task.status == 0
    assert task.tags == ["personal", "errands"]
    assert len(task.items) == 1
    assert task.items[0].title == "Get milk"
    assert len(task.reminders) == 1
    assert task.reminders[0].trigger == "TRIGGER:P0DT9H0M0S"
    assert task.start_date is not None
    assert task.due_date is not None
    assert task.time_zone == "America/New_York"
    assert task.repeat_flag == "RRULE:FREQ=WEEKLY;INTERVAL=1"
    assert task.sort_order == 5000
    assert task.etag == "abc123etag"
    assert task.creator == 9999
    assert task.comment_count == 2


def test_task_from_dict_minimal():
    task = Task.from_dict({"id": "t1", "projectId": "p1", "title": "Minimal"})
    assert task.id == "t1"
    assert task.content == ""
    assert task.priority == 0
    assert task.tags == []
    assert task.items == []
    assert task.reminders == []
    assert task.start_date is None
    assert task.due_date is None
    assert task.etag == ""
    assert task.attachments == []
    assert task.child_ids == []


def test_task_from_dict_null_fields():
    """Null tags/items/etc in API response are normalised to empty lists."""
    task = Task.from_dict(
        {
            "id": "t1",
            "projectId": "p1",
            "title": "Test",
            "tags": None,
            "items": None,
            "reminders": None,
            "attachments": None,
            "childIds": None,
            "repeatFlag": None,
            "repeatFrom": None,
            "parentId": None,
            "columnId": None,
        }
    )
    assert task.tags == []
    assert task.items == []
    assert task.reminders == []
    assert task.attachments == []
    assert task.child_ids == []
    assert task.repeat_flag == ""
    assert task.repeat_from == ""
    assert task.parent_id == ""
    assert task.column_id == ""


def test_task_to_dict_basic():
    task = Task.from_dict(TASK_DICT)
    d = task.to_dict()
    assert d["id"] == "task001"
    assert d["projectId"] == "proj001"
    assert d["title"] == "Buy groceries"
    assert d["priority"] == 3
    assert d["tags"] == ["personal", "errands"]
    assert len(d["items"]) == 1
    assert len(d["reminders"]) == 1
    assert "startDate" in d
    assert "dueDate" in d
    assert "timeZone" in d
    assert "repeatFlag" in d
    assert "repeatFrom" in d


def test_task_to_dict_includes_etag():
    task = Task.from_dict(TASK_DICT)
    d = task.to_dict()
    assert "etag" in d
    assert d["etag"] == "abc123etag"


def test_task_to_dict_omits_etag_when_empty():
    task = Task.from_dict({**TASK_DICT, "etag": ""})
    d = task.to_dict()
    assert "etag" not in d


def test_task_to_dict_includes_attachments():
    task = Task.from_dict({**TASK_DICT, "attachments": [{"fileKey": "file1"}]})
    d = task.to_dict()
    assert "attachments" in d
    assert d["attachments"] == [{"fileKey": "file1"}]


def test_task_to_dict_omits_attachments_when_empty():
    task = Task.from_dict({**TASK_DICT, "attachments": []})
    d = task.to_dict()
    assert "attachments" not in d


def test_task_to_dict_includes_child_ids():
    task = Task.from_dict({**TASK_DICT, "childIds": ["child1", "child2"]})
    d = task.to_dict()
    assert "childIds" in d
    assert d["childIds"] == ["child1", "child2"]


def test_task_to_dict_omits_child_ids_when_empty():
    task = Task.from_dict({**TASK_DICT, "childIds": []})
    d = task.to_dict()
    assert "childIds" not in d


def test_task_to_dict_omits_optional_when_empty():
    """Fields that are empty/falsy should not appear in to_dict()."""
    task = Task.from_dict({"id": "t1", "projectId": "p1", "title": "T"})
    d = task.to_dict()
    assert "timeZone" not in d
    assert "startDate" not in d
    assert "dueDate" not in d
    assert "repeatFlag" not in d
    assert "repeatFrom" not in d
    assert "parentId" not in d
    assert "columnId" not in d
    assert "etag" not in d
    assert "attachments" not in d
    assert "childIds" not in d


def test_task_round_trip():
    task = Task.from_dict(TASK_DICT)
    d = task.to_dict()
    task2 = Task.from_dict(d)
    assert task2.id == task.id
    assert task2.title == task.title
    assert task2.tags == task.tags
    assert task2.sort_order == task.sort_order
    assert task2.priority == task.priority
    assert len(task2.items) == len(task.items)
    assert len(task2.reminders) == len(task.reminders)


# ---------------------------------------------------------------------------
# SortOption
# ---------------------------------------------------------------------------


def test_sort_option_from_dict():
    so = SortOption.from_dict({"groupBy": "priority", "orderBy": "dueDate", "order": "asc"})
    assert so.group_by == "priority"
    assert so.order_by == "dueDate"
    assert so.order == "asc"


def test_sort_option_from_dict_none():
    so = SortOption.from_dict(None)
    assert so.group_by == "sortOrder"
    assert so.order_by == "sortOrder"
    assert so.order is None


def test_sort_option_to_dict():
    so = SortOption(group_by="priority", order_by="dueDate", order="asc")
    d = so.to_dict()
    assert d == {"groupBy": "priority", "orderBy": "dueDate", "order": "asc"}


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

PROJECT_DICT = {
    "id": "proj001",
    "name": "Work",
    "isOwner": True,
    "color": "#FF5733",
    "sortOrder": 0,
    "sortType": "sortOrder",
    "sortOption": {"groupBy": "sortOrder", "orderBy": "sortOrder", "order": None},
    "userCount": 1,
    "etag": "projetag",
    "modifiedTime": "2024-03-01T08:00:00.000+0000",
    "inAll": True,
    "showType": 0,
    "muted": False,
    "closed": None,
    "groupId": None,
    "viewMode": "list",
    "kind": "TASK",
    "teamId": None,
    "source": 0,
    "background": None,
}


def test_project_from_dict():
    proj = Project.from_dict(PROJECT_DICT)
    assert proj.id == "proj001"
    assert proj.name == "Work"
    assert proj.is_owner is True
    assert proj.color == "#FF5733"
    assert proj.etag == "projetag"
    assert proj.view_mode == "list"
    assert proj.kind == "TASK"
    assert proj.closed is None
    assert proj.group_id is None
    assert proj.modified_time is not None


def test_project_from_dict_minimal():
    proj = Project.from_dict({"id": "p1", "name": "Minimal"})
    assert proj.id == "p1"
    assert proj.name == "Minimal"
    assert proj.is_owner is True
    assert proj.sort_order == 0
    assert proj.view_mode == "list"


def test_project_to_dict_basic():
    proj = Project.from_dict(PROJECT_DICT)
    d = proj.to_dict()
    assert d["id"] == "proj001"
    assert d["name"] == "Work"
    assert d["sortOrder"] == 0
    assert "sortOption" in d
    assert d["viewMode"] == "list"
    assert d["kind"] == "TASK"
    assert d["inAll"] is True


def test_project_to_dict_includes_color():
    proj = Project.from_dict(PROJECT_DICT)
    d = proj.to_dict()
    assert "color" in d
    assert d["color"] == "#FF5733"


def test_project_to_dict_omits_color_when_none():
    proj = Project.from_dict({**PROJECT_DICT, "color": None})
    d = proj.to_dict()
    assert "color" not in d


def test_project_to_dict_includes_closed_when_set():
    proj = Project.from_dict({**PROJECT_DICT, "closed": True})
    d = proj.to_dict()
    assert "closed" in d
    assert d["closed"] is True


def test_project_to_dict_includes_closed_false():
    proj = Project.from_dict({**PROJECT_DICT, "closed": False})
    d = proj.to_dict()
    assert "closed" in d
    assert d["closed"] is False


def test_project_to_dict_omits_closed_when_none():
    proj = Project.from_dict({**PROJECT_DICT, "closed": None})
    d = proj.to_dict()
    assert "closed" not in d


def test_project_to_dict_includes_group_id():
    proj = Project.from_dict({**PROJECT_DICT, "groupId": "grp1"})
    d = proj.to_dict()
    assert "groupId" in d
    assert d["groupId"] == "grp1"


def test_project_to_dict_omits_group_id_when_none():
    proj = Project.from_dict({**PROJECT_DICT, "groupId": None})
    d = proj.to_dict()
    assert "groupId" not in d


def test_project_round_trip():
    proj = Project.from_dict(PROJECT_DICT)
    d = proj.to_dict()
    proj2 = Project.from_dict(d)
    assert proj2.id == proj.id
    assert proj2.name == proj.name
    assert proj2.view_mode == proj.view_mode


# ---------------------------------------------------------------------------
# ProjectGroup
# ---------------------------------------------------------------------------

GROUP_DICT = {
    "id": "grp001",
    "name": "My Folder",
    "showAll": True,
    "sortOrder": 100,
    "viewMode": "list",
    "sortType": "sortOrder",
    "etag": "grpetag",
}


def test_project_group_from_dict():
    g = ProjectGroup.from_dict(GROUP_DICT)
    assert g.id == "grp001"
    assert g.name == "My Folder"
    assert g.show_all is True
    assert g.sort_order == 100
    assert g.view_mode == "list"
    assert g.etag == "grpetag"


def test_project_group_to_dict():
    g = ProjectGroup.from_dict(GROUP_DICT)
    d = g.to_dict()
    assert d["id"] == "grp001"
    assert d["name"] == "My Folder"
    assert d["showAll"] is True
    assert d["sortOrder"] == 100


def test_project_group_round_trip():
    g = ProjectGroup.from_dict(GROUP_DICT)
    d = g.to_dict()
    g2 = ProjectGroup.from_dict(d)
    assert g2.id == g.id
    assert g2.name == g.name
    assert g2.sort_order == g.sort_order


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

TAG_DICT = {
    "name": "work",
    "rawName": "Work",
    "label": "Work",
    "sortOrder": 0,
    "sortType": "sortOrder",
    "color": "#3FBDDD",
    "etag": "tagetag",
    "type": 0,
    "sortOption": None,
}


def test_tag_from_dict():
    tag = Tag.from_dict(TAG_DICT)
    assert tag.name == "work"
    assert tag.raw_name == "Work"
    assert tag.label == "Work"
    assert tag.color == "#3FBDDD"
    assert tag.parent == ""  # no "/" in name


def test_tag_from_dict_subtag():
    """Tags with '/' are parsed to extract parent."""
    tag = Tag.from_dict({**TAG_DICT, "name": "work/meetings"})
    assert tag.name == "work/meetings"
    assert tag.parent == "work"


def test_tag_from_dict_nested_subtag():
    """Deep hierarchy: parent is everything before last '/'."""
    tag = Tag.from_dict({**TAG_DICT, "name": "a/b/c"})
    assert tag.parent == "a/b"


def test_tag_to_dict():
    tag = Tag.from_dict(TAG_DICT)
    d = tag.to_dict()
    assert d["name"] == "work"
    assert d["label"] == "Work"
    assert d["color"] == "#3FBDDD"
    assert "sortOrder" in d
    assert "sortType" in d


def test_tag_round_trip():
    tag = Tag.from_dict(TAG_DICT)
    d = tag.to_dict()
    tag2 = Tag.from_dict(d)
    assert tag2.name == tag.name
    assert tag2.color == tag.color


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

FILTER_DICT = {
    "id": "filt001",
    "name": "High Priority",
    "rule": '{"type":0,"and":[]}',
    "sortOrder": 0,
    "sortType": "priority",
    "viewMode": "list",
    "etag": "filtetag",
    "createdTime": "2024-03-01T08:00:00.000+0000",
    "modifiedTime": "2024-03-10T10:00:00.000+0000",
    "sortOption": None,
}


def test_filter_from_dict():
    f = Filter.from_dict(FILTER_DICT)
    assert f.id == "filt001"
    assert f.name == "High Priority"
    assert f.rule == '{"type":0,"and":[]}'
    assert f.sort_type == "priority"
    assert f.view_mode == "list"
    assert f.created_time is not None
    assert f.modified_time is not None


def test_filter_from_dict_minimal():
    f = Filter.from_dict({"id": "f1", "name": "Test"})
    assert f.id == "f1"
    assert f.name == "Test"
    assert f.rule == ""
    assert f.view_mode == "list"
    assert f.created_time is None


def test_filter_to_dict():
    f = Filter.from_dict(FILTER_DICT)
    d = f.to_dict()
    assert d["id"] == "filt001"
    assert d["name"] == "High Priority"
    assert d["rule"] == '{"type":0,"and":[]}'
    assert d["sortType"] == "priority"
    assert d["viewMode"] == "list"


def test_filter_round_trip():
    f = Filter.from_dict(FILTER_DICT)
    d = f.to_dict()
    f2 = Filter.from_dict(d)
    assert f2.id == f.id
    assert f2.name == f.name
    assert f2.rule == f.rule


# ---------------------------------------------------------------------------
# Habit
# ---------------------------------------------------------------------------

HABIT_DICT = {
    "id": "habit001",
    "name": "Morning Run",
    "iconRes": "habit_running",
    "color": "#7BC4FA",
    "sortOrder": 0,
    "status": 0,
    "encouragement": "Keep it up!",
    "totalCheckIns": 15,
    "type": "Boolean",
    "goal": 1,
    "step": 1,
    "unit": "Count",
    "repeatRule": "RRULE:FREQ=DAILY;INTERVAL=1",
    "reminders": [],
    "recordEnable": False,
    "sectionId": "-1",
    "targetDays": 30,
    "targetStartDate": 20240301,
    "completedCycles": 0,
    "createdTime": "2024-03-01T08:00:00.000+0000",
    "modifiedTime": "2024-03-10T10:00:00.000+0000",
    "archivedTime": None,
    "etag": "habitetag",
}


def test_habit_from_dict():
    h = Habit.from_dict(HABIT_DICT)
    assert h.id == "habit001"
    assert h.name == "Morning Run"
    assert h.icon_res == "habit_running"
    assert h.color == "#7BC4FA"
    assert h.status == 0
    assert h.encouragement == "Keep it up!"
    assert h.total_check_ins == 15
    assert h.type == "Boolean"
    assert h.goal == 1
    assert h.step == 1
    assert h.unit == "Count"
    assert h.repeat_rule == "RRULE:FREQ=DAILY;INTERVAL=1"
    assert h.target_days == 30
    assert h.target_start_date == 20240301
    assert h.created_time is not None
    assert h.archived_time is None
    assert h.etag == "habitetag"


def test_habit_from_dict_null_encouragement():
    """None encouragement from API is normalised to empty string."""
    h = Habit.from_dict({**HABIT_DICT, "encouragement": None})
    assert h.encouragement == ""


def test_habit_from_dict_null_reminders():
    h = Habit.from_dict({**HABIT_DICT, "reminders": None})
    assert h.reminders == []


def test_habit_to_dict():
    h = Habit.from_dict(HABIT_DICT)
    d = h.to_dict()
    assert d["id"] == "habit001"
    assert d["name"] == "Morning Run"
    assert d["iconRes"] == "habit_running"
    assert d["color"] == "#7BC4FA"
    assert d["status"] == 0
    assert d["type"] == "Boolean"
    assert d["goal"] == 1
    assert d["repeatRule"] == "RRULE:FREQ=DAILY;INTERVAL=1"
    assert d["targetDays"] == 30
    assert d["targetStartDate"] == 20240301


def test_habit_round_trip():
    h = Habit.from_dict(HABIT_DICT)
    d = h.to_dict()
    h2 = Habit.from_dict(d)
    assert h2.id == h.id
    assert h2.name == h.name
    assert h2.goal == h.goal


# ---------------------------------------------------------------------------
# HabitCheckin
# ---------------------------------------------------------------------------

CHECKIN_DICT = {
    "id": "checkin001",
    "habitId": "habit001",
    "status": 2,
    "value": 1.0,
    "checkinStamp": "20240315",
    "checkinTime": "2024-03-15T07:30:00.000+0000",
    "goal": 1.0,
    "etag": "checkinetag",
}


def test_habit_checkin_from_dict():
    c = HabitCheckin.from_dict(CHECKIN_DICT)
    assert c.id == "checkin001"
    assert c.habit_id == "habit001"
    assert c.status == 2
    assert c.value == 1.0
    assert c.checkin_stamp == "20240315"
    assert c.checkin_time is not None
    assert c.checkin_time.hour == 7
    assert c.goal == 1.0
    assert c.etag == "checkinetag"


def test_habit_checkin_from_dict_minimal():
    c = HabitCheckin.from_dict({})
    assert c.id == ""
    assert c.habit_id == ""
    assert c.status == 0
    assert c.value == 0
    assert c.checkin_time is None
    assert c.goal == 1


def test_habit_checkin_to_dict_includes_goal():
    c = HabitCheckin.from_dict(CHECKIN_DICT)
    d = c.to_dict()
    assert "goal" in d
    assert d["goal"] == 1.0


def test_habit_checkin_to_dict_includes_checkin_time():
    c = HabitCheckin.from_dict(CHECKIN_DICT)
    d = c.to_dict()
    assert "checkinTime" in d
    assert "2024-03-15" in d["checkinTime"]


def test_habit_checkin_to_dict_omits_checkin_time_when_none():
    c = HabitCheckin.from_dict({**CHECKIN_DICT, "checkinTime": None})
    d = c.to_dict()
    assert "checkinTime" not in d


def test_habit_checkin_round_trip():
    c = HabitCheckin.from_dict(CHECKIN_DICT)
    d = c.to_dict()
    c2 = HabitCheckin.from_dict(d)
    assert c2.id == c.id
    assert c2.habit_id == c.habit_id
    assert c2.status == c.status
    assert c2.value == c.value
    assert c2.checkin_stamp == c.checkin_stamp


# ---------------------------------------------------------------------------
# Column
# ---------------------------------------------------------------------------

COLUMN_DICT = {
    "id": "col001",
    "projectId": "proj001",
    "name": "In Progress",
    "sortOrder": 100,
    "etag": "coletag",
}


def test_column_from_dict():
    col = Column.from_dict(COLUMN_DICT)
    assert col.id == "col001"
    assert col.project_id == "proj001"
    assert col.name == "In Progress"
    assert col.sort_order == 100
    assert col.etag == "coletag"


def test_column_from_dict_minimal():
    col = Column.from_dict({"id": "c1"})
    assert col.id == "c1"
    assert col.project_id == ""
    assert col.name == ""
    assert col.sort_order == 0


def test_column_to_dict():
    col = Column.from_dict(COLUMN_DICT)
    d = col.to_dict()
    assert d["id"] == "col001"
    assert d["projectId"] == "proj001"
    assert d["name"] == "In Progress"
    assert d["sortOrder"] == 100


def test_column_round_trip():
    col = Column.from_dict(COLUMN_DICT)
    d = col.to_dict()
    col2 = Column.from_dict(d)
    assert col2.id == col.id
    assert col2.project_id == col.project_id
    assert col2.name == col.name
    assert col2.sort_order == col.sort_order
