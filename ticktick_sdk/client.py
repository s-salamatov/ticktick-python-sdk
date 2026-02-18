"""TickTick API client - reverse-engineered from the web app."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from ticktick_sdk.exceptions import (
    TickTickAuthError,
    TickTickForbiddenError,
    TickTickNotFoundError,
    TickTickRateLimitError,
    TickTickAPIError,
)

from ticktick_sdk.managers.task import TaskManager
from ticktick_sdk.managers.project import ProjectManager
from ticktick_sdk.managers.tag import TagManager
from ticktick_sdk.managers.filter import FilterManager
from ticktick_sdk.managers.habit import HabitManager
from ticktick_sdk.managers.search import SearchManager
from ticktick_sdk.managers.user import UserManager
from ticktick_sdk.managers.batch import BatchManager
from ticktick_sdk.managers.column import ColumnManager

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ticktick.com"

_SENSITIVE_ENDPOINTS = frozenset({"/api/v2/user/signon", "/api/v2/user/sign/mfa/code/verify"})

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0


class TickTickClient:
    """Main TickTick API client.

    Authenticate via login() or by setting a session token directly.

    All domain managers are accessible as attributes:
        client.task     - CRUD for tasks and subtasks
        client.project  - CRUD for lists / projects / project groups
        client.tag      - CRUD for tags and sub-tags
        client.filter   - CRUD for saved filters
        client.habit    - CRUD for habits and check-ins
        client.search   - Full-text and cloud search
        client.user     - User profile and preferences
        client.batch    - Batch sync operations
        client.column   - Kanban columns / sections
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        session: requests.Session | None = None,
        token: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.inbox_id: str = ""
        self._setup_session()
        if token:
            self.set_token(token)

        # Wire up managers
        self.task = TaskManager(self)
        self.project = ProjectManager(self)
        self.tag = TagManager(self)
        self.filter = FilterManager(self)
        self.habit = HabitManager(self)
        self.search = SearchManager(self)
        self.user = UserManager(self)
        self.batch = BatchManager(self)
        self.column = ColumnManager(self)

    def _setup_session(self) -> None:
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "x-device": '{"platform":"web","os":"macOS 10.15.7","device":"Chrome 120.0.0.0",'
                '"name":"","version":6010,"id":"web_client","channel":"website","campaign":"","websocket":""}',
                "Origin": "https://ticktick.com",
                "Referer": "https://ticktick.com/",
            }
        )

    def set_token(self, token: str) -> None:
        """Set the authentication cookie directly (t=<token>)."""
        self.session.cookies.set("t", token, domain="ticktick.com", path="/")

    # ── Authentication ────────────────────────────────────────────────

    def login(self, username: str, password: str, *, remember: bool = True) -> dict:
        """Sign in with email and password.

        Returns the signon response containing the auth token.
        For accounts with MFA, call verify_mfa() afterwards.
        """
        resp = self.request(
            "POST",
            "/api/v2/user/signon",
            params={"wc": "true", "remember": str(remember).lower()},
            json={"username": username, "password": password},
        )
        data = resp.json()
        if "token" in data:
            self.set_token(data["token"])
        if "inboxId" in data:
            self.inbox_id = data["inboxId"]
        logger.info("Logged in as %s", username)
        return data

    def check_mfa_setting(self) -> dict:
        """Check if MFA is required after signon."""
        return self.request("GET", "/api/v2/user/sign/mfa/setting").json()

    def verify_mfa(self, code: str) -> dict:
        """Verify MFA code after signon."""
        resp = self.request("POST", "/api/v2/user/sign/mfa/code/verify", json={"code": code})
        data = resp.json()
        if "token" in data:
            self.set_token(data["token"])
        return data

    # ── HTTP layer ────────────────────────────────────────────────────

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict | None = None,
        json: Any = None,
        data: Any = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an authenticated HTTP request to the TickTick API."""
        url = f"{self.base_url}{endpoint}"
        for attempt in range(MAX_RETRIES):
            resp = self.session.request(method, url, params=params, json=json, data=data, **kwargs)
            if resp.ok:
                return resp

            status = resp.status_code
            if endpoint in _SENSITIVE_ENDPOINTS:
                logger.error("HTTP %s %s -> %s: <redacted>", method, endpoint, status)
            else:
                logger.error("HTTP %s %s -> %s: %s", method, endpoint, status, resp.text[:500])

            if status == 429:
                retry_after_raw = resp.headers.get("Retry-After")
                retry_after = int(retry_after_raw) if retry_after_raw is not None else None
                if attempt < MAX_RETRIES - 1:
                    sleep_secs = retry_after if retry_after is not None else RETRY_BACKOFF * (2**attempt)
                    logger.warning(
                        "Rate limited; retrying in %.1f s (attempt %d/%d)", sleep_secs, attempt + 1, MAX_RETRIES
                    )
                    time.sleep(sleep_secs)
                    continue
                raise TickTickRateLimitError(retry_after=retry_after)

            if status == 401:
                raise TickTickAuthError(f"Authentication failed: {resp.text[:200]}")
            if status == 403:
                raise TickTickForbiddenError(f"Access denied: {resp.text[:200]}")
            if status == 404:
                raise TickTickNotFoundError(f"Resource not found: {resp.text[:200]}")

            # All other 4xx / 5xx
            try:
                body = resp.json()
                error_code = body.get("errorCode", "")
                error_message = body.get("errorMessage", "")
            except Exception:
                error_code = ""
                error_message = resp.text[:200]
            raise TickTickAPIError(status, error_code=error_code, error_message=error_message)

        # Should not be reached, but satisfies type checkers
        raise TickTickAPIError(0, error_message="Unexpected exit from retry loop")

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", endpoint, **kwargs)
