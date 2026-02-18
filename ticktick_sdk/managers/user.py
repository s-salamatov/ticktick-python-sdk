"""User management - profile, preferences, and account settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ticktick_sdk.client import TickTickClient


class UserManager:
    """User profile, preferences, status, and notification management."""

    def __init__(self, client: TickTickClient):
        self._c = client

    # ── Profile ───────────────────────────────────────────────────────

    def get_profile(self) -> dict:
        """Get the current user's profile."""
        return self._c.get("/api/v2/user/profile").json()

    def get_status(self) -> dict:
        """Get user account status (subscription, limits, etc)."""
        return self._c.get("/api/v2/user/status").json()

    def get_binding_info(self) -> dict:
        """Get account binding info (linked services)."""
        return self._c.get("/api/v2/user/userBindingInfo").json()

    # ── Preferences ───────────────────────────────────────────────────

    def get_settings(self, include_web: bool = True) -> dict:
        """Get user preferences / settings."""
        return self._c.get(
            "/api/v2/user/preferences/settings",
            params={"includeWeb": str(include_web).lower()},
        ).json()

    def update_settings(self, settings: dict) -> dict:
        """Update user preferences / settings."""
        return self._c.post("/api/v2/user/preferences/settings", json=settings).json()

    def get_daily_reminder(self) -> dict:
        """Get daily reminder settings."""
        return self._c.get("/api/v2/user/preferences/dailyReminder").json()

    def get_feature_prompts(self) -> dict:
        """Get feature prompt preferences (onboarding, tips)."""
        return self._c.get("/api/v2/user/preferences/featurePrompt").json()

    def get_habit_preferences(self, platform: str = "web") -> dict:
        """Get habit display preferences."""
        return self._c.get("/api/v2/user/preferences/habit", params={"platform": platform}).json()

    def get_ext_preferences(self, mtime: int = 0) -> dict:
        """Get extension/integration preferences."""
        return self._c.get("/api/v2/user/preferences/ext", params={"mtime": mtime}).json()

    # ── Account limits ────────────────────────────────────────────────

    def get_limits(self) -> dict:
        """Get account limits (max tasks, projects, etc)."""
        return self._c.get("/api/v2/configs/limits").json()

    def get_attachment_quota(self) -> bool:
        """Check if attachment quota is available."""
        return self._c.get("/api/v1/attachment/isUnderQuota").json()

    # ── Notifications ─────────────────────────────────────────────────

    def get_unread_notifications(self) -> list[dict]:
        """Get unread notifications."""
        return self._c.get("/api/v2/notification/unread").json()

    # ── MFA ───────────────────────────────────────────────────────────

    def get_mfa_settings(self) -> dict:
        """Get MFA (multi-factor authentication) settings."""
        return self._c.get("/api/v2/user/mfa").json()

    # ── Calendar ──────────────────────────────────────────────────────

    def get_calendar_accounts(self) -> list[dict]:
        """Get linked third-party calendar accounts."""
        return self._c.get("/api/v2/calendar/third/accounts").json()

    def get_calendar_subscriptions(self) -> list[dict]:
        """Get calendar subscriptions."""
        return self._c.get("/api/v2/calendar/subscription").json()

    def get_calendar_events(self) -> list[dict]:
        """Get all bound calendar events."""
        return self._c.get("/api/v2/calendar/bind/events/all").json()
