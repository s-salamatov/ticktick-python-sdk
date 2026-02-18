"""Unit tests for manager classes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest
import requests

from ticktick_sdk.client import TickTickClient
from ticktick_sdk.managers.task import TaskManager
from ticktick_sdk.managers.project import ProjectManager
from ticktick_sdk.managers.tag import TagManager
from ticktick_sdk.managers.filter import FilterManager
from ticktick_sdk.managers.habit import HabitManager
from ticktick_sdk.managers.column import ColumnManager
from ticktick_sdk.managers.batch import BatchManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_response(json_data=None, status_code: int = 200, text: str = ""):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.return_value = {}
    return resp


@pytest.fixture
def mock_client():
    """Return a MagicMock that mimics TickTickClient's interface."""
    client = MagicMock(spec=TickTickClient)
    client.inbox_id = "inbox123"
    # Wire up the batch manager with a real-ish mock
    batch = MagicMock(spec=BatchManager)
    client.batch = batch
    return client


# ---------------------------------------------------------------------------
# TaskManager
# ---------------------------------------------------------------------------

class TestTaskManager:

    @pytest.fixture
    def manager(self, mock_client):
        return TaskManager(mock_client)

    # -- create() -----------------------------------------------------------

    def test_create_generates_id_in_payload(self, manager, mock_client):
        task_resp = {
            "id": "generated_id",
            "projectId": "proj1",
            "title": "New task",
        }
        mock_client.post.return_value = make_response(task_resp)

        task = manager.create("New task", project_id="proj1")

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"]

        assert "id" in payload
        assert len(payload["id"]) == 24  # os.urandom(12).hex()
        assert payload["projectId"] == "proj1"
        assert payload["title"] == "New task"
        assert payload["status"] == 0

    def test_create_uses_inbox_when_no_project_id(self, manager, mock_client):
        mock_client.inbox_id = "inbox123"
        mock_client.post.return_value = make_response({
            "id": "x", "projectId": "inbox123", "title": "T",
        })

        manager.create("T")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["projectId"] == "inbox123"

    def test_create_falls_back_to_inbox_literal_when_no_inbox_id(self, manager, mock_client):
        mock_client.inbox_id = ""
        mock_client.post.return_value = make_response({
            "id": "x", "projectId": "inbox", "title": "T",
        })

        manager.create("T")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["projectId"] == "inbox"

    def test_create_includes_optional_fields(self, manager, mock_client):
        from datetime import datetime, timezone
        mock_client.post.return_value = make_response({
            "id": "x", "projectId": "p1", "title": "T",
        })

        dt = datetime(2024, 3, 15, 9, 0, tzinfo=timezone.utc)
        manager.create(
            "T",
            project_id="p1",
            content="body",
            priority=3,
            tags=["work"],
            start_date=dt,
            due_date=dt,
            is_all_day=True,
            time_zone="America/New_York",
            repeat_flag="RRULE:FREQ=DAILY;INTERVAL=1",
            parent_id="parent1",
            column_id="col1",
            kind="NOTE",
        )

        payload = mock_client.post.call_args[1]["json"]
        assert payload["content"] == "body"
        assert payload["priority"] == 3
        assert payload["tags"] == ["work"]
        assert "startDate" in payload
        assert "dueDate" in payload
        assert payload["isAllDay"] is True
        assert payload["timeZone"] == "America/New_York"
        assert payload["repeatFlag"] == "RRULE:FREQ=DAILY;INTERVAL=1"
        assert payload["parentId"] == "parent1"
        assert payload["columnId"] == "col1"
        assert payload["kind"] == "NOTE"

    def test_create_with_items_builds_subtasks(self, manager, mock_client):
        mock_client.post.return_value = make_response({
            "id": "x", "projectId": "p1", "title": "T",
        })

        manager.create("T", project_id="p1", items=[{"title": "Sub 1"}, {"title": "Sub 2"}])

        payload = mock_client.post.call_args[1]["json"]
        assert len(payload["items"]) == 2
        assert payload["items"][0]["title"] == "Sub 1"
        assert payload["items"][1]["title"] == "Sub 2"
        # Each item gets an auto-generated id
        for item in payload["items"]:
            assert "id" in item
            assert "status" in item
            assert "sortOrder" in item

    def test_create_posts_to_correct_endpoint(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id": "x", "projectId": "p1", "title": "T"})
        manager.create("T", project_id="p1")
        mock_client.post.assert_called_once()
        endpoint = mock_client.post.call_args[0][0]
        assert endpoint == "/api/v2/task"

    # -- delete() -----------------------------------------------------------

    def test_delete_uses_batch_endpoint(self, manager, mock_client):
        mock_client.post.return_value = make_response({})

        manager.delete("task123", "proj1")

        mock_client.post.assert_called_once_with(
            "/api/v2/batch/task",
            json={"delete": [{"taskId": "task123", "projectId": "proj1"}]},
        )

    def test_batch_delete_sends_all_tasks(self, manager, mock_client):
        mock_client.post.return_value = make_response({})
        tasks = [
            {"taskId": "t1", "projectId": "p1"},
            {"taskId": "t2", "projectId": "p2"},
        ]
        manager.batch_delete(tasks)
        mock_client.post.assert_called_once_with(
            "/api/v2/batch/task",
            json={"delete": tasks},
        )

    # -- get_completed() ---------------------------------------------------

    def test_get_completed_with_project_id(self, manager, mock_client):
        task_data = [{"id": "t1", "projectId": "p1", "title": "Done"}]
        mock_client.get.return_value = make_response(task_data)

        tasks = manager.get_completed("p1")

        mock_client.get.assert_called_once()
        endpoint = mock_client.get.call_args[0][0]
        assert "/api/v2/project/p1/completed/" in endpoint
        assert len(tasks) == 1
        assert tasks[0].id == "t1"

    def test_get_completed_without_project_id_uses_all_endpoint(self, manager, mock_client):
        mock_client.get.return_value = make_response([])

        manager.get_completed()

        endpoint = mock_client.get.call_args[0][0]
        assert "/api/v2/project/all/completed/" in endpoint

    def test_get_completed_skips_empty_date_params(self, manager, mock_client):
        """Empty from_date/to_date should NOT be included in params."""
        mock_client.get.return_value = make_response([])

        manager.get_completed("p1", from_date="", to_date="")

        params = mock_client.get.call_args[1]["params"]
        assert "from" not in params
        assert "to" not in params
        assert "limit" in params

    def test_get_completed_includes_date_params_when_set(self, manager, mock_client):
        mock_client.get.return_value = make_response([])

        manager.get_completed("p1", from_date="2024-03-01 00:00:00", to_date="2024-03-31 23:59:59")

        params = mock_client.get.call_args[1]["params"]
        assert params["from"] == "2024-03-01 00:00:00"
        assert params["to"] == "2024-03-31 23:59:59"

    # -- get_all() ----------------------------------------------------------

    def test_get_all_extracts_tasks_from_sync_bean(self, manager, mock_client):
        sync_data = {
            "syncTaskBean": {
                "update": [
                    {"id": "t1", "projectId": "p1", "title": "Task 1"},
                    {"id": "t2", "projectId": "p2", "title": "Task 2"},
                ]
            }
        }
        mock_client.batch.check.return_value = sync_data

        tasks = manager.get_all()

        assert len(tasks) == 2
        assert tasks[0].id == "t1"
        assert tasks[1].id == "t2"

    def test_get_all_handles_empty_sync_bean(self, manager, mock_client):
        mock_client.batch.check.return_value = {}
        tasks = manager.get_all()
        assert tasks == []

    def test_get_all_handles_missing_update_key(self, manager, mock_client):
        mock_client.batch.check.return_value = {"syncTaskBean": {}}
        tasks = manager.get_all()
        assert tasks == []


# ---------------------------------------------------------------------------
# TagManager
# ---------------------------------------------------------------------------

class TestTagManager:

    @pytest.fixture
    def manager(self, mock_client):
        return TagManager(mock_client)

    # -- create() -----------------------------------------------------------

    def test_create_uses_batch_endpoint(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id2etag": {}, "id2error": {}})
        mock_client.batch.full_sync.return_value = {
            "tags": [{"name": "newtag", "label": "newtag", "sortOrder": 0, "color": ""}]
        }

        manager.create("newtag")

        # First post should go to /api/v2/batch/tag
        first_call = mock_client.post.call_args
        assert first_call[0][0] == "/api/v2/batch/tag"
        payload = first_call[1]["json"]
        assert "add" in payload
        assert len(payload["add"]) == 1
        assert payload["add"][0]["name"] == "newtag"

    def test_create_prefixes_parent_name(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id2etag": {}, "id2error": {}})
        mock_client.batch.full_sync.return_value = {"tags": []}

        manager.create("child", parent="parent")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["add"][0]["name"] == "parent/child"

    def test_create_does_not_double_prefix(self, manager, mock_client):
        """If name already contains '/', parent is not prepended."""
        mock_client.post.return_value = make_response({"id2etag": {}, "id2error": {}})
        mock_client.batch.full_sync.return_value = {"tags": []}

        manager.create("parent/child", parent="parent")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["add"][0]["name"] == "parent/child"

    def test_create_label_defaults_to_name(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id2etag": {}, "id2error": {}})
        mock_client.batch.full_sync.return_value = {"tags": []}

        manager.create("mytag")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["add"][0]["label"] == "mytag"

    def test_create_returns_tag_from_sync_if_found(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id2etag": {}, "id2error": {}})
        mock_client.batch.full_sync.return_value = {
            "tags": [{"name": "work", "label": "Work", "color": "#FF0000", "sortOrder": 0}]
        }

        tag = manager.create("work")
        assert tag.name == "work"
        assert tag.color == "#FF0000"

    # -- delete() -----------------------------------------------------------

    def test_delete_simple_tag_uses_delete_endpoint(self, manager, mock_client):
        mock_client.delete.return_value = make_response({})

        manager.delete("work")

        mock_client.delete.assert_called_once()
        endpoint = mock_client.delete.call_args[0][0]
        assert "/api/v2/tag/" in endpoint
        assert "work" in endpoint

    def test_delete_subtag_uses_batch_endpoint(self, manager, mock_client):
        """Sub-tags (names with '/') must use the batch endpoint."""
        mock_client.post.return_value = make_response({})

        manager.delete("parent/child")

        mock_client.post.assert_called_once_with(
            "/api/v2/batch/tag",
            json={"delete": ["parent/child"]},
        )
        # Direct DELETE should not be called
        mock_client.delete.assert_not_called()

    def test_delete_subtag_does_not_call_direct_delete(self, manager, mock_client):
        mock_client.post.return_value = make_response({})
        manager.delete("a/b")
        mock_client.delete.assert_not_called()


# ---------------------------------------------------------------------------
# FilterManager
# ---------------------------------------------------------------------------

class TestFilterManager:

    @pytest.fixture
    def manager(self, mock_client):
        return FilterManager(mock_client)

    # -- create() -----------------------------------------------------------

    def test_create_uses_batch_endpoint(self, manager, mock_client):
        mock_client.post.return_value = make_response(
            {"id2etag": {"filt1": "etag123"}, "id2error": {}}
        )
        mock_client.batch.full_sync.return_value = {
            "filters": [{"id": "filt1", "name": "My Filter", "rule": "{}", "sortOrder": 0, "sortType": "", "viewMode": "list"}]
        }

        manager.create("My Filter", rule={"type": 0, "and": []})

        mock_client.post.assert_called_once()
        endpoint = mock_client.post.call_args[0][0]
        assert endpoint == "/api/v2/batch/filter"
        payload = mock_client.post.call_args[1]["json"]
        assert "add" in payload
        assert payload["add"][0]["name"] == "My Filter"

    def test_create_serialises_dict_rule_to_json(self, manager, mock_client):
        import json
        mock_client.post.return_value = make_response({"id2etag": {}, "id2error": {}})

        manager.create("F", rule={"type": 0})

        payload = mock_client.post.call_args[1]["json"]
        rule_str = payload["add"][0]["rule"]
        assert isinstance(rule_str, str)
        assert json.loads(rule_str) == {"type": 0}

    def test_create_accepts_string_rule(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id2etag": {}, "id2error": {}})

        manager.create("F", rule='{"type":0}')

        payload = mock_client.post.call_args[1]["json"]
        assert payload["add"][0]["rule"] == '{"type":0}'

    def test_create_returns_filter_from_sync_when_id2etag_has_entry(self, manager, mock_client):
        mock_client.post.return_value = make_response(
            {"id2etag": {"filt_abc": "etag1"}, "id2error": {}}
        )
        mock_client.batch.full_sync.return_value = {
            "filters": [
                {"id": "filt_abc", "name": "Test", "rule": "{}", "sortOrder": 0, "sortType": "", "viewMode": "list"}
            ]
        }

        result = manager.create("Test", rule="{}")
        # create() returns a raw dict when found in full_sync
        assert result["id"] == "filt_abc"

    # -- delete() -----------------------------------------------------------

    def test_delete_uses_batch_endpoint(self, manager, mock_client):
        mock_client.post.return_value = make_response({})

        manager.delete("filt123")

        mock_client.post.assert_called_once_with(
            "/api/v2/batch/filter",
            json={"delete": ["filt123"]},
        )


# ---------------------------------------------------------------------------
# ProjectManager
# ---------------------------------------------------------------------------

class TestProjectManager:

    @pytest.fixture
    def manager(self, mock_client):
        return ProjectManager(mock_client)

    # -- get_all() ----------------------------------------------------------

    def test_get_all_returns_projects(self, manager, mock_client):
        mock_client.batch.check.return_value = {
            "projectProfiles": [
                {"id": "p1", "name": "Work"},
                {"id": "p2", "name": "Personal"},
            ]
        }

        projects = manager.get_all()

        assert len(projects) == 2
        assert projects[0].id == "p1"
        assert projects[1].name == "Personal"

    def test_get_all_handles_none_from_delta_sync(self, manager, mock_client):
        """If projectProfiles is None (delta sync omits unchanged), return []."""
        mock_client.batch.check.return_value = {"projectProfiles": None}

        projects = manager.get_all()

        assert projects == []

    def test_get_all_handles_missing_project_profiles_key(self, manager, mock_client):
        mock_client.batch.check.return_value = {}
        projects = manager.get_all()
        assert projects == []

    def test_get_all_uses_checkpoint_zero(self, manager, mock_client):
        """get_all() must do a full sync (checkpoint=0)."""
        mock_client.batch.check.return_value = {"projectProfiles": []}
        manager.get_all()
        mock_client.batch.check.assert_called_once_with(0)

    # -- create() -----------------------------------------------------------

    def test_create_posts_to_project_endpoint(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id": "p_new", "name": "New List"})

        project = manager.create("New List")

        mock_client.post.assert_called_once()
        endpoint = mock_client.post.call_args[0][0]
        assert endpoint == "/api/v2/project"

    def test_create_includes_optional_color(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id": "p1", "name": "Colored"})
        manager.create("Colored", color="#FF5733")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["color"] == "#FF5733"

    def test_create_omits_color_when_none(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id": "p1", "name": "Plain"})
        manager.create("Plain")
        payload = mock_client.post.call_args[1]["json"]
        assert "color" not in payload

    # -- delete() -----------------------------------------------------------

    def test_delete_calls_delete_endpoint(self, manager, mock_client):
        mock_client.delete.return_value = make_response({})
        manager.delete("proj123")
        mock_client.delete.assert_called_once_with("/api/v2/project/proj123")

    # -- get_groups() -------------------------------------------------------

    def test_get_groups_returns_groups(self, manager, mock_client):
        mock_client.batch.check.return_value = {
            "projectGroups": [
                {"id": "g1", "name": "Folder A"},
                {"id": "g2", "name": "Folder B"},
            ]
        }
        groups = manager.get_groups()
        assert len(groups) == 2
        assert groups[0].id == "g1"

    def test_get_groups_handles_none(self, manager, mock_client):
        mock_client.batch.check.return_value = {"projectGroups": None}
        groups = manager.get_groups()
        assert groups == []


# ---------------------------------------------------------------------------
# HabitManager
# ---------------------------------------------------------------------------

class TestHabitManager:

    @pytest.fixture
    def manager(self, mock_client):
        return HabitManager(mock_client)

    # -- get_checkins() with dict-of-lists response -------------------------

    def test_get_checkins_handles_flat_list_response(self, manager, mock_client):
        checkins = [
            {"id": "c1", "habitId": "h1", "checkinStamp": "20240315", "status": 2, "value": 1},
            {"id": "c2", "habitId": "h1", "checkinStamp": "20240316", "status": 2, "value": 1},
        ]
        mock_client.post.return_value = make_response(checkins)

        result = manager.get_checkins(["h1"])

        assert len(result) == 2
        assert result[0].id == "c1"
        assert result[1].id == "c2"

    def test_get_checkins_handles_dict_of_lists_response(self, manager, mock_client):
        """TickTick sometimes returns {checkins: {habitId: [checkin, ...]}}."""
        response_data = {
            "checkins": {
                "habit001": [
                    {"id": "c1", "habitId": "habit001", "checkinStamp": "20240315", "status": 2, "value": 1},
                    {"id": "c2", "habitId": "habit001", "checkinStamp": "20240316", "status": 2, "value": 1},
                ],
                "habit002": [
                    {"id": "c3", "habitId": "habit002", "checkinStamp": "20240315", "status": 2, "value": 1},
                ],
            }
        }
        mock_client.post.return_value = make_response(response_data)

        result = manager.get_checkins(["habit001", "habit002"])

        assert len(result) == 3
        ids = {c.id for c in result}
        assert ids == {"c1", "c2", "c3"}

    def test_get_checkins_empty_dict_of_lists(self, manager, mock_client):
        mock_client.post.return_value = make_response({"checkins": {}})
        result = manager.get_checkins([])
        assert result == []

    def test_get_checkins_posts_to_correct_endpoint(self, manager, mock_client):
        mock_client.post.return_value = make_response([])
        manager.get_checkins(["h1"])
        endpoint = mock_client.post.call_args[0][0]
        assert endpoint == "/api/v2/habitCheckins/query"

    def test_get_checkins_includes_habit_ids_in_payload(self, manager, mock_client):
        mock_client.post.return_value = make_response([])
        manager.get_checkins(["h1", "h2"])
        payload = mock_client.post.call_args[1]["json"]
        assert payload["habitIds"] == ["h1", "h2"]

    def test_get_checkins_excludes_habit_ids_when_none(self, manager, mock_client):
        """When habit_ids is None, it should not appear in the payload."""
        mock_client.post.return_value = make_response([])
        manager.get_checkins(None)
        payload = mock_client.post.call_args[1]["json"]
        assert "habitIds" not in payload

    def test_get_checkins_includes_after_stamp_when_set(self, manager, mock_client):
        mock_client.post.return_value = make_response([])
        manager.get_checkins(None, after_stamp="20240301")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["afterStamp"] == "20240301"

    def test_get_checkins_excludes_after_stamp_when_empty(self, manager, mock_client):
        mock_client.post.return_value = make_response([])
        manager.get_checkins(None, after_stamp="")
        payload = mock_client.post.call_args[1]["json"]
        assert "afterStamp" not in payload

    # -- get_all() ----------------------------------------------------------

    def test_get_all_habits(self, manager, mock_client):
        habits_data = [
            {"id": "h1", "name": "Run"},
            {"id": "h2", "name": "Read"},
        ]
        mock_client.get.return_value = make_response(habits_data)

        habits = manager.get_all()

        assert len(habits) == 2
        assert habits[0].id == "h1"
        assert habits[1].name == "Read"

    def test_get_all_calls_habits_endpoint(self, manager, mock_client):
        mock_client.get.return_value = make_response([])
        manager.get_all()
        mock_client.get.assert_called_once_with("/api/v2/habits")

    # -- create() -----------------------------------------------------------

    def test_create_posts_to_habits_endpoint(self, manager, mock_client):
        habit_data = {"id": "h_new", "name": "Exercise"}
        mock_client.post.return_value = make_response(habit_data)

        with patch("ticktick_sdk.managers.habit.date") as mock_date:
            mock_date.today.return_value.strftime.return_value = "20240315"
            manager.create("Exercise")

        endpoint = mock_client.post.call_args[0][0]
        assert endpoint == "/api/v2/habits"

    def test_create_includes_required_fields(self, manager, mock_client):
        mock_client.post.return_value = make_response({"id": "h1", "name": "Test"})

        with patch("ticktick_sdk.managers.habit.date") as mock_date:
            mock_date.today.return_value.strftime.return_value = "20240315"
            manager.create("Test")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["name"] == "Test"
        assert "type" in payload
        assert "goal" in payload
        assert "repeatRule" in payload
        assert "status" in payload
        assert payload["status"] == 0


# ---------------------------------------------------------------------------
# ColumnManager
# ---------------------------------------------------------------------------

class TestColumnManager:

    @pytest.fixture
    def manager(self, mock_client):
        return ColumnManager(mock_client)

    def test_get_all_handles_list_response(self, manager, mock_client):
        columns_data = [
            {"id": "c1", "projectId": "p1", "name": "Todo", "sortOrder": 0},
            {"id": "c2", "projectId": "p1", "name": "Done", "sortOrder": 1},
        ]
        mock_client.get.return_value = make_response(columns_data)

        cols = manager.get_all()

        assert len(cols) == 2
        assert cols[0].id == "c1"

    def test_get_all_handles_dict_response(self, manager, mock_client):
        response = {
            "columns": [
                {"id": "c1", "projectId": "p1", "name": "Todo", "sortOrder": 0},
            ]
        }
        mock_client.get.return_value = make_response(response)

        cols = manager.get_all()
        assert len(cols) == 1
        assert cols[0].name == "Todo"

    def test_get_by_project_calls_correct_endpoint(self, manager, mock_client):
        mock_client.get.return_value = make_response([])
        manager.get_by_project("proj1")
        mock_client.get.assert_called_once_with("/api/v2/column/project/proj1")

    def test_create_posts_then_fetches_column(self, manager, mock_client):
        # First call: POST to create, returns id2etag
        mock_client.post.return_value = make_response({"id2etag": {}, "id2error": {}})

        # get_by_project call returns a column with the generated id
        # We need to capture the generated id from the POST call
        created_column = None

        def fake_get(endpoint):
            # Return the column that was "created"
            nonlocal created_column
            if created_column is None:
                return make_response([])
            return make_response([created_column])

        # Simulate: after post, get_by_project returns a column
        col_id_holder = []

        def fake_post(endpoint, json):
            col_id_holder.append(json["id"])
            return make_response({"id2etag": {json["id"]: "etag1"}, "id2error": {}})

        mock_client.post.side_effect = fake_post

        def fake_get_project(endpoint):
            if col_id_holder:
                return make_response([{
                    "id": col_id_holder[0],
                    "projectId": "proj1",
                    "name": "Backlog",
                    "sortOrder": 0,
                }])
            return make_response([])

        mock_client.get.side_effect = fake_get_project

        col = manager.create("proj1", "Backlog")

        assert col.name == "Backlog"
        assert col.project_id == "proj1"

    def test_delete_raises_not_implemented(self, manager):
        with pytest.raises(NotImplementedError):
            manager.delete("col1", "proj1")


# ---------------------------------------------------------------------------
# BatchManager
# ---------------------------------------------------------------------------

class TestBatchManager:

    @pytest.fixture
    def manager(self, mock_client):
        return BatchManager(mock_client)

    def test_check_calls_correct_endpoint(self, manager, mock_client):
        mock_client.get.return_value = make_response({"checkPoint": 12345})
        manager.check(0)
        mock_client.get.assert_called_once_with("/api/v3/batch/check/0")

    def test_check_updates_checkpoint(self, manager, mock_client):
        mock_client.get.return_value = make_response({"checkPoint": 99999})
        manager.check(0)
        assert manager.checkpoint == 99999

    def test_check_updates_inbox_id(self, manager, mock_client):
        mock_client.get.return_value = make_response({
            "checkPoint": 1,
            "inboxId": "inbox_from_sync",
        })
        manager.check(0)
        assert mock_client.inbox_id == "inbox_from_sync"

    def test_check_uses_last_checkpoint_when_none_given(self, manager, mock_client):
        mock_client.get.return_value = make_response({"checkPoint": 500})
        manager._checkpoint = 300
        manager.check()  # no arg -> uses stored checkpoint
        mock_client.get.assert_called_once_with("/api/v3/batch/check/300")

    def test_full_sync_resets_checkpoint_to_zero(self, manager, mock_client):
        mock_client.get.return_value = make_response({"checkPoint": 1})
        manager._checkpoint = 999
        manager.full_sync()
        mock_client.get.assert_called_with("/api/v3/batch/check/0")

    def test_delta_sync_uses_stored_checkpoint(self, manager, mock_client):
        mock_client.get.return_value = make_response({"checkPoint": 200})
        manager._checkpoint = 100
        manager.delta_sync()
        mock_client.get.assert_called_with("/api/v3/batch/check/100")
