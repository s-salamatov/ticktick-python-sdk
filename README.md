# TickTick Python SDK

![status: unofficial](https://img.shields.io/badge/status-unofficial-orange)
![python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![CI: pending](https://img.shields.io/badge/CI-pending-lightgrey)

> **Disclaimer:** This is an unofficial, reverse-engineered SDK based on the TickTick web app API.
> It is not affiliated with, endorsed by, or supported by TickTick or its parent company.
> API endpoints may change without notice. Use at your own risk.

## Installation

```bash
pip install ticktick-sdk        # future PyPI release
```

Until the package is published, install directly from source:

```bash
pip install requests
# Clone the repo and add the project root to your PYTHONPATH
```

## Quick Start

```python
from ticktick_sdk import TickTickClient

client = TickTickClient()
client.login("your@email.com", "your_password")

# List all tasks
tasks = client.task.get_all()
for t in tasks:
    print(f"[{t.priority}] {t.title} — {t.project_id}")
```

## Authentication

### Email / Password Login

```python
client = TickTickClient()
result = client.login("email@example.com", "password")

# With MFA enabled:
mfa = client.check_mfa_setting()
if mfa.get("mfaType"):
    client.verify_mfa(input("Enter MFA code: "))
```

### Token-Based Auth (Browser Cookie)

If you already hold a session token (value of the `t` cookie from a logged-in browser session):

```python
client = TickTickClient(token="your_session_token")
# or
client = TickTickClient()
client.set_token("your_session_token")
```

## API Coverage

### Tasks (`client.task`)

```python
from datetime import datetime

# Create
task = client.task.create(
    "Buy groceries",
    project_id="inbox",          # defaults to inbox when omitted
    priority=3,                  # 0=none, 1=low, 3=medium, 5=high
    tags=["errands"],
    due_date=datetime(2026, 3, 1),
    is_all_day=True,
    content="Markdown notes here",
    items=[                       # Subtasks / checklist items
        {"title": "Milk"},
        {"title": "Bread"},
    ],
)

# Read
task = client.task.get("task_id", "project_id")
all_tasks = client.task.get_all()
project_tasks = client.task.get_by_project("project_id")
completed = client.task.get_completed(project_id="project_id")
all_completed = client.task.get_completed_in_all()
trash = client.task.get_trash()

# Update
task.title = "Buy groceries and snacks"
task.priority = 5
client.task.update(task)

# Partial update (fetch + merge + save)
client.task.update_fields("task_id", "project_id", title="New title", priority=1)

# Complete / Uncomplete
client.task.complete("task_id", "project_id")
client.task.uncomplete("task_id", "project_id")

# Delete — uses POST /api/v2/batch/task with {"delete": [...]}
client.task.delete("task_id", "project_id")

# Move to another list
client.task.move("task_id", "old_project_id", "new_project_id")

# Set parent for nested tasks
client.task.set_parent("child_task_id", "project_id", "parent_task_id")

# Batch operations (single request)
client.task.batch_create([task1_dict, task2_dict])
client.task.batch_update([task1_dict, task2_dict])
client.task.batch_delete([{"taskId": "id1", "projectId": "pid1"}])
```

### Subtasks (`client.task`)

Subtasks are checklist items embedded within a parent task.

```python
# Add a subtask
client.task.add_subtask("task_id", "project_id", "Subtask title")

# Mark a subtask complete
client.task.complete_subtask("task_id", "project_id", "subtask_id")

# Remove a subtask
client.task.remove_subtask("task_id", "project_id", "subtask_id")
```

### Projects / Lists (`client.project`)

```python
# Create
project = client.project.create(
    "Work Tasks",
    color="#FF5733",
    view_mode="kanban",    # "list", "kanban", or "timeline"
    kind="TASK",           # "TASK" or "NOTE"
    group_id="folder_id",  # place inside a folder (optional)
)

# Read
projects = client.project.get_all()    # uses full sync (checkpoint=0)
project  = client.project.get("project_id")
groups   = client.project.get_groups()

# Update — PUT returns empty body; the SDK re-fetches the project automatically
project.name = "Updated Name"
client.project.update(project)
client.project.rename("project_id", "New Name")

# Delete / Archive
client.project.delete("project_id")
client.project.archive("project_id")
client.project.unarchive("project_id")

# Project Groups (Folders)
group = client.project.create_group("My Folder")
client.project.move_to_group("project_id", "group_id")
client.project.update_group(group)
client.project.delete_group("group_id")

# Templates
templates = client.project.get_templates()
```

### Columns / Sections (`client.column`)

Columns represent Kanban sections within a project. Create and update use the
same `POST /api/v2/column` endpoint — the API upserts by column ID.

```python
# Read
all_cols     = client.column.get_all()
proj_cols    = client.column.get_by_project("project_id")

# Create
col = client.column.create("project_id", "In Progress")

# Rename / Update
client.column.rename("column_id", "project_id", "Done")
col.name = "Shipped"
client.column.update(col)

# Delete is NOT supported — see Known Limitations
```

### Tags (`client.tag`)

Tags are hierarchical: a sub-tag is stored as `"parent/child"`. Create and
update go through `POST /api/v2/batch/tag`; simple-tag delete uses
`DELETE /api/v2/tag/{name}`.

```python
# Read — uses full sync (checkpoint=0)
tags     = client.tag.get_all()
tag      = client.tag.get("work")
children = client.tag.get_children("work")   # returns tags named "work/..."

# Create
client.tag.create("work", color="#FF0000")
client.tag.create("work/urgent")             # sub-tag via name
client.tag.create_subtag("work", "urgent")   # sub-tag via helper

# Update properties (color, sort order, etc.)
tag.color = "#00FF00"
client.tag.update(tag)

# Rename across all tasks
client.tag.rename("old_name", "new_name")

# Delete — simple tags: DELETE /api/v2/tag/{name}
#          sub-tags (contain "/"): POST /api/v2/batch/tag {"delete": [...]}
client.tag.delete("work")
client.tag.delete("work/urgent")

# Completed tasks filtered by tag
completed = client.tag.get_completed_tasks(["work", "urgent"], limit=50)
```

### Filters / Smart Lists (`client.filter`)

All filter mutations (create, update, delete) use `POST /api/v2/batch/filter`.

```python
from ticktick_sdk.managers.filter import FilterManager

# Read — uses full sync (checkpoint=0)
filters = client.filter.get_all()
filt    = client.filter.get("filter_id")

# Build a rule and create
rule = FilterManager.build_rule(
    project_ids=["project_id_1"],
    priority=[5, 3],          # high and medium
    tag_names=["urgent"],
)
client.filter.create("High Priority Urgent", rule, view_mode="kanban")

# Update
filt.name = "Renamed Filter"
client.filter.update(filt)

# Delete
client.filter.delete("filter_id")
```

### Habits (`client.habit`)

Habit **reads** and **check-ins** work correctly with cookie auth.
Habit **create / update / delete** (`POST /api/v2/habits`, `PUT`, `DELETE`)
all return HTTP 405 when authenticating via the cookie-based reverse-engineered
session. Treat habits as **read-only** unless you have a proper OAuth token.

```python
# Read
habits   = client.habit.get_all()
active   = client.habit.get_active()
archived = client.habit.get_archived()
habit    = client.habit.get("habit_id")

# Check-in (works with cookie auth)
client.habit.checkin("habit_id")                      # today, status=checked
client.habit.checkin("habit_id", stamp="20260301")    # specific date (YYYYMMDD)
client.habit.checkin("habit_id", value=30, status=2)  # numeric Real habit

# Batch check-in
client.habit.batch_checkin([
    {"habitId": "id1", "checkinStamp": "20260301", "value": 1, "status": 2},
    {"habitId": "id2", "checkinStamp": "20260301", "value": 1, "status": 2},
])

# Query check-ins
# Returns a flat list of HabitCheckin objects.
# Raw API format: {"checkins": {habit_id: [checkin, ...]}}
checkins = client.habit.get_checkins(["habit_id"], after_stamp="20260101")

# Preferences (read-only)
prefs = client.habit.get_preferences()
```

### Search (`client.search`)

```python
# Cloud search across all content
results = client.search.search("meeting notes")

# Convenience wrapper returning Task objects
tasks = client.search.search_tasks("tennis")

# Client-side filtering over the batch sync snapshot
high_priority  = client.search.filter_tasks(priority=5)
tagged         = client.search.filter_tasks(tag="urgent", project_id="proj_id")
with_due_dates = client.search.filter_tasks(has_due_date=True)
```

### User & Preferences (`client.user`)

```python
profile       = client.user.get_profile()
status        = client.user.get_status()
settings      = client.user.get_settings()
limits        = client.user.get_limits()
notifications = client.user.get_unread_notifications()
calendar      = client.user.get_calendar_events()
```

### Batch Sync (`client.batch`)

The batch sync endpoint is the canonical way TickTick transfers data between
client and server. Several managers call `check(0)` (full sync) internally to
guarantee complete data because delta sync may return `None` for unchanged
collections such as `projectProfiles`, `tags`, and `filters`.

```python
# Full sync — returns everything (tasks, projects, tags, filters, …)
data = client.batch.full_sync()
# Keys: syncTaskBean, projectProfiles, projectGroups, tags, filters,
#       checkPoint, inboxId, syncTaskOrderBean, remindChanges

# Delta sync — only changes since the last checkpoint
changes = client.batch.delta_sync()

# Manual checkpoint management
print(client.batch.checkpoint)
client.batch.checkpoint = 0
```

## Data Models

All API objects are Python dataclasses with `from_dict()` / `to_dict()` helpers.

| Model | Key Fields |
|-------|------------|
| `Task` | id, project_id, title, content, priority, status, tags, items, due_date, start_date, repeat_flag |
| `Subtask` | id, title, status, sort_order |
| `Project` | id, name, color, view_mode, kind, group_id |
| `ProjectGroup` | id, name, show_all |
| `Tag` | name, label, color, parent (for sub-tags) |
| `Filter` | id, name, rule, view_mode |
| `Habit` | id, name, type, goal, unit, repeat_rule, status |
| `HabitCheckin` | id, habit_id, value, checkin_stamp, status |
| `Column` | id, project_id, name, sort_order |

### Priority Values

| Value | Meaning |
|-------|---------|
| 0 | None |
| 1 | Low |
| 3 | Medium |
| 5 | High |

### Task / Subtask Status Values

| Value | Meaning |
|-------|---------|
| 0 | Open |
| 2 | Completed |

## API Endpoints

Base URL: `https://api.ticktick.com`

Only endpoints verified to work with cookie-based auth are listed.

### Authentication
| Method | Endpoint | Notes |
|--------|----------|-------|
| `POST` | `/api/v2/user/signon` | Sign in, returns token |
| `GET` | `/api/v2/user/sign/mfa/setting` | Check MFA requirement |
| `POST` | `/api/v2/user/sign/mfa/code/verify` | Verify MFA code |

### Batch Sync
| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/api/v3/batch/check/{checkpoint}` | Full or delta data sync |
| `POST` | `/api/v2/batch/task` | Task batch ops: `{add/update/delete: [...]}` |
| `POST` | `/api/v2/batch/taskParent` | Set parent-child task relationships |
| `POST` | `/api/v2/batch/tag` | Tag batch ops: `{add/update/delete: [...]}` |
| `POST` | `/api/v2/batch/filter` | Filter batch ops: `{add/update/delete: [...]}` |

### Tasks
| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/api/v2/task/{taskId}?projectId={id}` | Fetch single task |
| `POST` | `/api/v2/task` | Create task |
| `POST` | `/api/v2/task/{taskId}` | Update task |
| `POST` | `/api/v2/batch/task` | Delete: `{"delete": [{"taskId","projectId"}]}` |
| `GET` | `/api/v2/project/{id}/completed/` | Completed tasks by project |
| `GET` | `/api/v2/project/all/completed/` | All completed tasks |
| `GET` | `/api/v2/project/all/completedInAll/` | Completed tasks (broad query) |
| `GET` | `/api/v2/project/all/trash/pagination` | Trashed tasks |

### Projects
| Method | Endpoint | Notes |
|--------|----------|-------|
| `POST` | `/api/v2/project` | Create project |
| `PUT` | `/api/v2/project/{id}` | Update project (returns empty body on success) |
| `DELETE` | `/api/v2/project/{id}` | Delete project and all its tasks |
| `POST` | `/api/v2/projectGroup` | Create project group (folder) |
| `PUT` | `/api/v2/projectGroup/{id}` | Update project group |
| `DELETE` | `/api/v2/projectGroup/{id}` | Delete project group |

### Tags
| Method | Endpoint | Notes |
|--------|----------|-------|
| `POST` | `/api/v2/batch/tag` | Create: `{"add": [tag_dict]}` |
| `POST` | `/api/v2/batch/tag` | Update: `{"update": [tag_dict]}` |
| `PUT` | `/api/v2/tag/rename` | Rename tag across all tasks |
| `DELETE` | `/api/v2/tag/{name}` | Delete simple tag (no `/` in name) |
| `POST` | `/api/v2/batch/tag` | Delete sub-tag: `{"delete": ["parent/child"]}` |
| `POST` | `/api/v2/tag/completedTask` | Completed tasks filtered by tags |

### Columns / Sections
| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/api/v2/column?from={ts}` | All columns (modified since timestamp) |
| `GET` | `/api/v2/column/project/{id}` | Columns for a specific project |
| `POST` | `/api/v2/column` | Create or update column (upsert by id) |

### Habits (Read-Only)
| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/api/v2/habits` | Get all habits |
| `POST` | `/api/v2/habitCheckins` | Record a single check-in |
| `POST` | `/api/v2/habitCheckins/query` | Query check-ins; response: `{"checkins": {habit_id: [...]}}` |
| `POST` | `/api/v2/habits/batch` | Batch check-ins |
| `GET` | `/api/v2/user/preferences/habit` | Habit preferences |

### Search
| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/api/v2/search/all?keywords={q}` | Cloud full-text search |

### User
| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/api/v2/user/profile` | User profile |
| `GET` | `/api/v2/user/status` | Account status and subscription |
| `GET` | `/api/v2/user/preferences/settings` | User settings |
| `POST` | `/api/v2/user/preferences/settings` | Update user settings |
| `GET` | `/api/v2/configs/limits` | Account limits |
| `GET` | `/api/v2/notification/unread` | Unread notifications |
| `GET` | `/api/v2/calendar/third/accounts` | Linked third-party calendars |
| `GET` | `/api/v2/calendar/subscription` | Calendar subscriptions |
| `GET` | `/api/v2/calendar/bind/events/all` | All bound calendar events |

## Known Limitations

- **Habits are read-only.** `POST /api/v2/habits`, `PUT /api/v2/habits/{id}`,
  and `DELETE /api/v2/habits/{id}` all return HTTP 405 when using cookie-based
  authentication. Only GET and check-in endpoints work. Habit create/update/delete
  methods are included in the SDK for future compatibility but will raise an
  error at runtime.

- **Column delete is not supported.** No standalone column delete endpoint has
  been discovered. `client.column.delete()` raises `NotImplementedError`.
  Deleting the parent project removes all its columns.

- **Delta sync may omit unchanged data.** `GET /api/v3/batch/check/{cp}` with
  a non-zero checkpoint can return `null` for `projectProfiles`, `tags`, and
  `filters` when nothing has changed. Managers that need a complete list
  (`project.get_all()`, `tag.get_all()`, `filter.get_all()`) always call
  `check(0)` (full sync) to guarantee correctness.

- **Rate limits.** TickTick may throttle requests. No official rate limit
  documentation exists. The SDK does not implement automatic back-off beyond
  basic error propagation.

- **No official OAuth support.** This SDK authenticates via the same session
  cookie the web app uses. There is no public OAuth 2.0 client ID available
  for third-party use.

## Architecture

```
ticktick_sdk/
    __init__.py          # Public exports and __version__
    client.py            # TickTickClient: auth, HTTP layer, manager wiring
    models.py            # Dataclasses: Task, Project, Tag, Filter, Habit, …
    exceptions.py        # Typed HTTP error classes
    managers/
        task.py          # Task CRUD, subtasks, batch ops, completion
        project.py       # Project/list CRUD, groups, archive, templates
        tag.py           # Tag/sub-tag CRUD, tag-based queries
        filter.py        # Saved filter CRUD with rule builder
        habit.py         # Habit reads, check-ins (write ops return 405)
        search.py        # Cloud search and client-side filtering
        user.py          # Profile, preferences, notifications, calendar
        batch.py         # Core batch sync (full and delta)
        column.py        # Kanban columns / sections
```

## Contributing

Issues and pull requests are welcome. Before opening a PR please:

1. Verify the endpoint behaviour against a live TickTick session.
2. Add or update the relevant manager and model.
3. Update the endpoint table above to reflect the tested behaviour.
