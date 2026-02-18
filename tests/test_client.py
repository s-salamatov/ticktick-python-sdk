"""Unit tests for TickTickClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from ticktick_sdk.client import TickTickClient, BASE_URL, MAX_RETRIES
from ticktick_sdk.exceptions import (
    TickTickAuthError,
    TickTickForbiddenError,
    TickTickNotFoundError,
    TickTickRateLimitError,
    TickTickAPIError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_response(status_code: int, json_data=None, text: str = "", headers=None):
    """Build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = status_code < 400
    resp.text = text or ""
    resp.headers = headers or {}
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.return_value = {}
    return resp


@pytest.fixture
def mock_session():
    """Return a mock Session whose .request() can be configured per test."""
    session = MagicMock(spec=requests.Session)
    session.cookies = MagicMock()
    # Use a MagicMock for headers so that .update() calls don't fail
    session.headers = MagicMock()
    return session


@pytest.fixture
def client(mock_session):
    """Return a TickTickClient wired to a mock session."""
    return TickTickClient(session=mock_session)


# ---------------------------------------------------------------------------
# set_token
# ---------------------------------------------------------------------------

def test_set_token_sets_cookie(client, mock_session):
    client.set_token("mytoken123")
    mock_session.cookies.set.assert_called_once_with(
        "t", "mytoken123", domain="ticktick.com", path="/"
    )


# ---------------------------------------------------------------------------
# request() – success path
# ---------------------------------------------------------------------------

def test_request_success(client, mock_session):
    ok_resp = make_response(200, json_data={"key": "value"})
    mock_session.request.return_value = ok_resp

    resp = client.request("GET", "/api/v2/something")

    mock_session.request.assert_called_once_with(
        "GET",
        f"{BASE_URL}/api/v2/something",
        params=None,
        json=None,
        data=None,
    )
    assert resp.json() == {"key": "value"}


def test_request_passes_params_and_json(client, mock_session):
    ok_resp = make_response(200, json_data={})
    mock_session.request.return_value = ok_resp

    client.request("POST", "/api/v2/task", params={"p": "1"}, json={"title": "t"})

    mock_session.request.assert_called_once_with(
        "POST",
        f"{BASE_URL}/api/v2/task",
        params={"p": "1"},
        json={"title": "t"},
        data=None,
    )


# ---------------------------------------------------------------------------
# request() – HTTP error handling
# ---------------------------------------------------------------------------

def test_request_raises_auth_error_on_401(client, mock_session):
    mock_session.request.return_value = make_response(401, text="Unauthorized")
    with pytest.raises(TickTickAuthError):
        client.request("GET", "/api/v2/protected")


def test_request_raises_forbidden_error_on_403(client, mock_session):
    mock_session.request.return_value = make_response(403, text="Forbidden")
    with pytest.raises(TickTickForbiddenError):
        client.request("GET", "/api/v2/protected")


def test_request_raises_not_found_error_on_404(client, mock_session):
    mock_session.request.return_value = make_response(404, text="Not found")
    with pytest.raises(TickTickNotFoundError):
        client.request("GET", "/api/v2/nonexistent")


def test_request_raises_api_error_on_500(client, mock_session):
    mock_session.request.return_value = make_response(
        500,
        json_data={"errorCode": "INTERNAL", "errorMessage": "Server error"},
    )
    with pytest.raises(TickTickAPIError) as exc_info:
        client.request("GET", "/api/v2/error")
    err = exc_info.value
    assert err.status_code == 500
    assert err.error_code == "INTERNAL"
    assert err.error_message == "Server error"


def test_request_raises_api_error_with_non_json_body(client, mock_session):
    resp = make_response(500, text="Internal Server Error")
    resp.json.side_effect = ValueError("No JSON")
    mock_session.request.return_value = resp
    with pytest.raises(TickTickAPIError) as exc_info:
        client.request("GET", "/api/v2/error")
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# request() – 429 retry logic
# ---------------------------------------------------------------------------

def test_request_retries_on_429_then_succeeds(client, mock_session):
    """First call returns 429, second returns 200."""
    rate_limited = make_response(429, text="Too Many Requests")
    rate_limited.headers = {}
    ok_resp = make_response(200, json_data={"ok": True})

    mock_session.request.side_effect = [rate_limited, ok_resp]

    with patch("ticktick_sdk.client.time.sleep") as mock_sleep:
        resp = client.request("GET", "/api/v2/something")

    assert resp.json() == {"ok": True}
    assert mock_sleep.call_count == 1
    assert mock_session.request.call_count == 2


def test_request_respects_retry_after_header(client, mock_session):
    """Uses Retry-After header value for sleep duration."""
    rate_limited = make_response(429, text="Too Many Requests")
    rate_limited.headers = {"Retry-After": "5"}
    ok_resp = make_response(200, json_data={})

    mock_session.request.side_effect = [rate_limited, ok_resp]

    with patch("ticktick_sdk.client.time.sleep") as mock_sleep:
        client.request("GET", "/api/v2/something")

    mock_sleep.assert_called_once_with(5)


def test_request_raises_rate_limit_after_max_retries(client, mock_session):
    """All retries exhausted -> TickTickRateLimitError."""
    rate_limited = make_response(429, text="Too Many Requests")
    rate_limited.headers = {}

    mock_session.request.side_effect = [rate_limited] * MAX_RETRIES

    with patch("ticktick_sdk.client.time.sleep"):
        with pytest.raises(TickTickRateLimitError):
            client.request("GET", "/api/v2/something")

    assert mock_session.request.call_count == MAX_RETRIES


def test_rate_limit_error_carries_retry_after(client, mock_session):
    """TickTickRateLimitError.retry_after is set from the header."""
    rate_limited = make_response(429, text="rate limited")
    rate_limited.headers = {"Retry-After": "30"}

    mock_session.request.side_effect = [rate_limited] * MAX_RETRIES

    with patch("ticktick_sdk.client.time.sleep"):
        with pytest.raises(TickTickRateLimitError) as exc_info:
            client.request("GET", "/api/v2/something")

    assert exc_info.value.retry_after == 30


def test_rate_limit_error_retry_after_none_when_no_header(client, mock_session):
    rate_limited = make_response(429, text="rate limited")
    rate_limited.headers = {}

    mock_session.request.side_effect = [rate_limited] * MAX_RETRIES

    with patch("ticktick_sdk.client.time.sleep"):
        with pytest.raises(TickTickRateLimitError) as exc_info:
            client.request("GET", "/api/v2/something")

    assert exc_info.value.retry_after is None


# ---------------------------------------------------------------------------
# request() – sensitive endpoint log redaction
# ---------------------------------------------------------------------------

def test_sensitive_endpoint_response_is_redacted(client, mock_session):
    """Auth endpoints must not log the response body."""
    bad_resp = make_response(401, text="bad credentials")
    mock_session.request.return_value = bad_resp

    with patch("ticktick_sdk.client.logger") as mock_logger:
        with pytest.raises(TickTickAuthError):
            client.request("POST", "/api/v2/user/signon", json={"username": "u", "password": "p"})

    # The error log call for sensitive endpoints must include "<redacted>"
    # and must NOT include the raw response text.
    log_calls = [str(c) for c in mock_logger.error.call_args_list]
    assert any("<redacted>" in c for c in log_calls), (
        "Expected '<redacted>' in logger.error call for sensitive endpoint"
    )
    assert not any("bad credentials" in c for c in log_calls), (
        "Response body must not appear in logs for sensitive endpoints"
    )


def test_mfa_endpoint_response_is_redacted(client, mock_session):
    """MFA verify endpoint is also sensitive."""
    bad_resp = make_response(401, text="bad mfa code")
    mock_session.request.return_value = bad_resp

    with patch("ticktick_sdk.client.logger") as mock_logger:
        with pytest.raises(TickTickAuthError):
            client.request("POST", "/api/v2/user/sign/mfa/code/verify", json={"code": "123456"})

    log_calls = [str(c) for c in mock_logger.error.call_args_list]
    assert any("<redacted>" in c for c in log_calls)
    assert not any("bad mfa code" in c for c in log_calls)


def test_non_sensitive_endpoint_logs_response_body(client, mock_session):
    """Non-sensitive error responses ARE logged."""
    bad_resp = make_response(500, text="internal server error details")
    bad_resp.json.return_value = {"errorCode": "", "errorMessage": ""}
    mock_session.request.return_value = bad_resp

    with patch("ticktick_sdk.client.logger") as mock_logger:
        with pytest.raises(TickTickAPIError):
            client.request("GET", "/api/v2/tasks")

    log_calls = [str(c) for c in mock_logger.error.call_args_list]
    assert any("internal server error details" in c for c in log_calls)


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------

def test_login_sets_token_and_inbox_id(client, mock_session):
    login_response = make_response(200, json_data={
        "token": "auth_token_xyz",
        "inboxId": "inbox_abc",
        "username": "test@example.com",
    })
    mock_session.request.return_value = login_response

    result = client.login("test@example.com", "password123")

    assert result["token"] == "auth_token_xyz"
    assert client.inbox_id == "inbox_abc"
    # set_token should have been called -> cookies.set should have been called
    mock_session.cookies.set.assert_called_with("t", "auth_token_xyz", domain="ticktick.com", path="/")


def test_login_without_token_in_response(client, mock_session):
    """If the response has no token (e.g. MFA required), inbox_id is still set."""
    login_response = make_response(200, json_data={
        "inboxId": "inbox_abc",
        "mfaRequired": True,
    })
    mock_session.request.return_value = login_response

    result = client.login("u@example.com", "pass")
    assert "token" not in result
    assert client.inbox_id == "inbox_abc"
    # set_token should NOT have been called
    mock_session.cookies.set.assert_not_called()


def test_login_uses_signon_endpoint(client, mock_session):
    """login() POSTs to the correct endpoint with expected params."""
    login_response = make_response(200, json_data={"token": "t", "inboxId": "i"})
    mock_session.request.return_value = login_response

    client.login("user@example.com", "secret")

    call_args = mock_session.request.call_args
    assert call_args[0][0] == "POST"
    assert "/api/v2/user/signon" in call_args[0][1]
    assert call_args[1]["params"]["wc"] == "true"


# ---------------------------------------------------------------------------
# Convenience method wrappers
# ---------------------------------------------------------------------------

def test_get_delegates_to_request(client, mock_session):
    ok_resp = make_response(200, json_data={})
    mock_session.request.return_value = ok_resp
    client.get("/api/v2/foo", params={"x": "1"})
    mock_session.request.assert_called_once_with(
        "GET", f"{BASE_URL}/api/v2/foo", params={"x": "1"}, json=None, data=None
    )


def test_post_delegates_to_request(client, mock_session):
    ok_resp = make_response(200, json_data={})
    mock_session.request.return_value = ok_resp
    client.post("/api/v2/task", json={"title": "T"})
    mock_session.request.assert_called_once_with(
        "POST", f"{BASE_URL}/api/v2/task", params=None, json={"title": "T"}, data=None
    )


def test_put_delegates_to_request(client, mock_session):
    ok_resp = make_response(200, json_data={})
    mock_session.request.return_value = ok_resp
    client.put("/api/v2/project/p1", json={"name": "Updated"})
    mock_session.request.assert_called_once_with(
        "PUT", f"{BASE_URL}/api/v2/project/p1", params=None, json={"name": "Updated"}, data=None
    )


def test_delete_delegates_to_request(client, mock_session):
    ok_resp = make_response(200, json_data={})
    mock_session.request.return_value = ok_resp
    client.delete("/api/v2/project/p1")
    mock_session.request.assert_called_once_with(
        "DELETE", f"{BASE_URL}/api/v2/project/p1", params=None, json=None, data=None
    )
