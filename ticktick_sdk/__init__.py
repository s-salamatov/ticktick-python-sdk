"""
TickTick Python SDK - Reverse-engineered from the TickTick web app API.

Usage:
    from ticktick_sdk import TickTickClient

    client = TickTickClient()
    client.login("email@example.com", "password")

    # List all projects
    projects = client.project.get_all()

    # Create a task
    task = client.task.create("My task", project_id="inbox")
"""

from ticktick_sdk.client import TickTickClient
from ticktick_sdk.exceptions import (
    TickTickError,
    TickTickAuthError,
    TickTickAPIError,
    TickTickRateLimitError,
)
from ticktick_sdk.models import (
    Task, Project, Tag, Filter, Habit, HabitCheckin,
    Subtask, Column, ProjectGroup, Reminder, SortOption,
)

__all__ = [
    "TickTickClient",
    "TickTickError",
    "TickTickAuthError",
    "TickTickAPIError",
    "TickTickRateLimitError",
    "Task",
    "Project",
    "Tag",
    "Filter",
    "Habit",
    "HabitCheckin",
    "Subtask",
    "Column",
    "ProjectGroup",
    "Reminder",
    "SortOption",
]

__version__ = "0.1.0"
