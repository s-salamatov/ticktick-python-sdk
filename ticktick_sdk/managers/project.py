"""Project (list) management - CRUD for projects and project groups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ticktick_sdk.models import Project, ProjectGroup

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class ProjectManager:
    """Manage projects (lists), project groups (folders), and archive."""

    def __init__(self, client: TickTickClient):
        self._c = client

    # ── Read ──────────────────────────────────────────────────────────

    def get_all(self) -> list[Project]:
        """Get all projects via full sync (checkpoint=0).

        Delta sync may omit unchanged projects, so a full sync is used
        to guarantee the complete list is returned.
        """
        data = self._c.batch.check(0)
        return [Project.from_dict(p) for p in data.get("projectProfiles") or []]

    def get(self, project_id: str) -> Project:
        """Get a single project by ID."""
        projects = self.get_all()
        for p in projects:
            if p.id == project_id:
                return p
        raise ValueError(f"Project {project_id} not found")

    def get_groups(self) -> list[ProjectGroup]:
        """Get all project groups (folders)."""
        data = self._c.batch.check()
        return [ProjectGroup.from_dict(g) for g in data.get("projectGroups") or []]

    # ── Create ────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        *,
        color: str | None = None,
        view_mode: str = "list",
        kind: str = "TASK",
        group_id: str | None = None,
        sort_order: int = 0,
    ) -> Project:
        """Create a new project (list).

        Args:
            name: Project name.
            color: Hex color code e.g. "#FF5733".
            view_mode: "list", "kanban", or "timeline".
            kind: "TASK" or "NOTE".
            group_id: Parent project group (folder) ID.
            sort_order: Sort position.
        """
        payload: dict[str, Any] = {
            "name": name,
            "sortOrder": sort_order,
            "viewMode": view_mode,
            "kind": kind,
        }
        if color:
            payload["color"] = color
        if group_id:
            payload["groupId"] = group_id
        resp = self._c.post("/api/v2/project", json=payload)
        return Project.from_dict(resp.json())

    # ── Update ────────────────────────────────────────────────────────

    def update(self, project: Project) -> Project:
        """Update a project. Pass a modified Project object."""
        resp = self._c.put(f"/api/v2/project/{project.id}", json=project.to_dict())
        # The API may return an empty body on success; re-fetch in that case.
        if resp.text.strip():
            return Project.from_dict(resp.json())
        return self.get(project.id)

    def rename(self, project_id: str, new_name: str) -> Project:
        """Rename a project."""
        project = self.get(project_id)
        project.name = new_name
        return self.update(project)

    # ── Delete / Archive ──────────────────────────────────────────────

    def delete(self, project_id: str) -> None:
        """Delete a project and all its tasks."""
        self._c.delete(f"/api/v2/project/{project_id}")

    def archive(self, project_id: str) -> None:
        """Archive a project (soft close)."""
        project = self.get(project_id)
        project.closed = True
        self.update(project)

    def unarchive(self, project_id: str) -> None:
        """Unarchive a project."""
        project = self.get(project_id)
        project.closed = False
        self.update(project)

    # ── Project Groups (Folders) ──────────────────────────────────────

    def create_group(self, name: str, *, sort_order: int = 0) -> ProjectGroup:
        """Create a project group (folder)."""
        resp = self._c.post(
            "/api/v2/projectGroup",
            json={
                "name": name,
                "sortOrder": sort_order,
            },
        )
        return ProjectGroup.from_dict(resp.json())

    def update_group(self, group: ProjectGroup) -> ProjectGroup:
        """Update a project group."""
        resp = self._c.put(f"/api/v2/projectGroup/{group.id}", json=group.to_dict())
        return ProjectGroup.from_dict(resp.json())

    def delete_group(self, group_id: str) -> None:
        """Delete a project group."""
        self._c.delete(f"/api/v2/projectGroup/{group_id}")

    def move_to_group(self, project_id: str, group_id: str | None) -> Project:
        """Move a project into a group, or out of a group (group_id=None)."""
        project = self.get(project_id)
        project.group_id = group_id
        return self.update(project)

    # ── Templates ─────────────────────────────────────────────────────

    def get_templates(self) -> list[dict]:
        """Get available project templates."""
        return self._c.get("/api/v2/templates").json()

    def get_project_templates(self, timestamp: int = 0) -> list[dict]:
        """Get user's project templates."""
        return self._c.get("/api/v2/projectTemplates/all", params={"timestamp": timestamp}).json()
