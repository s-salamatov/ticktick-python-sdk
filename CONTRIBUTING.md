# Contributing

## Getting an auth token

This SDK authenticates using the `t` session cookie that the TickTick web app sets after login.

**Via browser (recommended for exploration):**

1. Open [https://ticktick.com](https://ticktick.com) and log in.
2. Open DevTools (F12) → **Application** → **Cookies** → `https://ticktick.com`.
3. Copy the value of the `t` cookie.
4. Pass it to the client: `TickTickClient(token="<value>")`.

**Via `login()` (programmatic):**

```python
from ticktick_sdk import TickTickClient

client = TickTickClient()
client.login("you@example.com", "password")  # sets the token automatically
```

> Note: cookie-based auth grants read/write access to tasks, projects, tags, and filters.
> Habit **write** endpoints return HTTP 405 with cookie auth — habits are effectively read-only.

---

## Development setup

```bash
git clone https://github.com/your-org/ticktick-reverse-api.git
cd ticktick-reverse-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Running tests

```bash
pytest tests/
```

---

## Project structure

```
ticktick_sdk/
    client.py       # TickTickClient — HTTP session, auth, raw request helpers
    models.py       # Dataclasses for Task, Project, Tag, Habit, etc.
    exceptions.py   # SDK-specific exceptions
    managers/       # One manager per resource type
        batch.py    # Low-level batch API wrapper (POST /api/v2/batch/<entity>)
        task.py     # TaskManager
        project.py  # ProjectManager
        tag.py      # TagManager
        habit.py    # HabitManager (read-only)
        column.py   # ColumnManager
        filter.py   # FilterManager
        search.py   # SearchManager
        user.py     # UserManager
```

---

## Key conventions

**Batch API.** Most mutating operations (create, update, delete) go through
`POST /api/v2/batch/<entity>` with `add`, `update`, and `delete` lists in the
body — not individual REST endpoints. Use `managers/batch.py` as the foundation
for new write operations.

**Full sync over delta sync.** When a manager needs to read a list of items it
calls `check(0)` (full sync) rather than a delta sync, because delta sync
responses can return `None` for unchanged data and make parsing fragile.

**Models.** All resource models are `@dataclass` classes in `models.py` and
expose `from_dict(data: dict)` and `to_dict() -> dict` for serialization.
Always keep `from_dict` tolerant of unknown keys so new API fields do not break
existing code.

**Tag name casing.** The TickTick API stores and matches tag names
case-insensitively (always lowercase internally). Normalize tag names to
lowercase before sending them.

**Habits are read-only.** `GET /api/v2/habits` works fine; write endpoints
(`POST`, `PUT`) return HTTP 405 with cookie auth. Do not add habit write methods
without verifying against a session that has write access.

---

## Discovering new endpoints

1. Open TickTick in Chrome/Firefox, open DevTools → **Network** tab.
2. Perform the action you want to replicate, then filter by `api/v2`.
3. Export a **HAR** file (right-click → "Save all as HAR") and inspect the
   request/response payloads.
4. The `openapi.yaml` in the repo root documents already-discovered endpoints —
   add any new ones there as part of your PR.

---

## Pull request guidelines

- Test your changes with `pytest tests/` before opening a PR.
- If you add or change a public method, update `README.md` accordingly.
- Keep PRs focused: one feature or fix per PR.
- Add a short entry to the `openapi.yaml` for any new endpoint you use.
