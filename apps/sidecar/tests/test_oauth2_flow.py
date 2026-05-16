"""Tests for the OAuth2 PKCE flow endpoints."""

from __future__ import annotations

import base64
import hashlib
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from theridion_sidecar.api.oauth2 import generate_pkce, _cb
from theridion_sidecar.main import create_app


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_callback_state():
    """Reset callback server state between tests."""
    _cb.code = None
    _cb.state = None
    _cb.error = None
    _cb.received = False
    _cb.server = None
    _cb.thread = None
    yield
    # Ensure callback server is stopped after each test
    if _cb.server is not None:
        try:
            _cb.server.server_close()
        except Exception:
            pass
        _cb.server = None
    _cb.received = True  # Signal thread to stop
    import time
    # Give thread a moment to exit, then reset state cleanly
    if _cb.thread is not None and _cb.thread.is_alive():
        _cb.thread.join(timeout=2)
    _cb.thread = None
    _cb.received = False
    _cb.code = None
    _cb.state = None
    _cb.error = None


class TestPKCEGeneration:
    """Test PKCE code_verifier and code_challenge generation."""

    def test_generate_pkce_returns_tuple(self):
        verifier, challenge = generate_pkce()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)

    def test_verifier_length(self):
        verifier, _ = generate_pkce()
        # token_urlsafe(96) produces 128 chars
        assert 43 <= len(verifier) <= 128

    def test_challenge_is_s256_of_verifier(self):
        verifier, challenge = generate_pkce()
        expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
        assert challenge == expected_challenge

    def test_unique_per_call(self):
        v1, c1 = generate_pkce()
        v2, c2 = generate_pkce()
        assert v1 != v2
        assert c1 != c2


class TestAuthorizeUrl:
    """Test the authorize-url endpoint."""

    def test_basic_authorize_url(self, client: TestClient):
        resp = client.post("/api/auth/oauth2/authorize-url", json={
            "auth_url": "https://accounts.google.com/o/oauth2/auth",
            "client_id": "my-client-id",
            "scope": "openid email",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert "state" in data
        assert data["code_verifier"] is not None
        assert data["code_challenge"] is not None
        # URL should contain PKCE params
        assert "code_challenge=" in data["url"]
        assert "code_challenge_method=S256" in data["url"]
        assert "client_id=my-client-id" in data["url"]

    def test_authorize_url_without_pkce(self, client: TestClient):
        resp = client.post("/api/auth/oauth2/authorize-url", json={
            "auth_url": "https://example.com/auth",
            "client_id": "test",
            "use_pkce": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code_verifier"] is None
        assert data["code_challenge"] is None
        assert "code_challenge" not in data["url"]

    def test_authorize_url_with_custom_state(self, client: TestClient):
        resp = client.post("/api/auth/oauth2/authorize-url", json={
            "auth_url": "https://example.com/auth",
            "client_id": "test",
            "state": "my-custom-state",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "my-custom-state"
        assert "state=my-custom-state" in data["url"]

    def test_authorize_url_preserves_existing_params(self, client: TestClient):
        resp = client.post("/api/auth/oauth2/authorize-url", json={
            "auth_url": "https://example.com/auth?audience=my-api",
            "client_id": "test",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "audience=my-api" in data["url"]


class TestCallbackServer:
    """Test callback server start/stop/poll."""

    def test_start_callback_server(self, client: TestClient):
        resp = client.post("/api/auth/oauth2/callback-server/start", json={
            "port": 19876,
            "timeout_seconds": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["port"] == 19876
        assert data["status"] == "listening"
        # Clean up
        client.post("/api/auth/oauth2/callback-server/stop")

    def test_poll_waiting(self, client: TestClient):
        client.post("/api/auth/oauth2/callback-server/start", json={
            "port": 19877,
            "timeout_seconds": 5,
        })
        resp = client.get("/api/auth/oauth2/callback-server/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "waiting"
        # Clean up
        client.post("/api/auth/oauth2/callback-server/stop")

    def test_stop_callback_server(self, client: TestClient):
        client.post("/api/auth/oauth2/callback-server/start", json={
            "port": 19878,
            "timeout_seconds": 10,
        })
        resp = client.post("/api/auth/oauth2/callback-server/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"

    def test_poll_not_running(self, client: TestClient):
        resp = client.get("/api/auth/oauth2/callback-server/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_running"

    def test_double_start_returns_409(self, client: TestClient):
        client.post("/api/auth/oauth2/callback-server/start", json={
            "port": 19879,
            "timeout_seconds": 10,
        })
        resp = client.post("/api/auth/oauth2/callback-server/start", json={
            "port": 19880,
            "timeout_seconds": 10,
        })
        assert resp.status_code == 409
        # Clean up
        client.post("/api/auth/oauth2/callback-server/stop")


class TestTokenExchange:
    """Test token exchange with a mocked token endpoint."""

    def test_exchange_success(self, client: TestClient):
        mock_response = httpx.Response(
            200,
            json={
                "access_token": "test-access-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "test-refresh-token",
                "scope": "openid email",
            },
        )
        with patch("theridion_sidecar.api.oauth2.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_instance

            resp = client.post("/api/auth/oauth2/token", json={
                "token_url": "https://example.com/token",
                "client_id": "my-client",
                "client_secret": "my-secret",
                "code": "auth-code-123",
                "redirect_uri": "http://localhost:9876/oauth2/callback",
                "code_verifier": "test-verifier",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "test-access-token"
        assert data["refresh_token"] == "test-refresh-token"
        assert data["expires_in"] == 3600

    def test_exchange_error_response(self, client: TestClient):
        mock_response = httpx.Response(
            400,
            json={"error": "invalid_grant"},
            text='{"error": "invalid_grant"}',
        )
        with patch("theridion_sidecar.api.oauth2.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_instance

            resp = client.post("/api/auth/oauth2/token", json={
                "token_url": "https://example.com/token",
                "client_id": "my-client",
                "code": "bad-code",
            })

        assert resp.status_code == 400


class TestTokenRefresh:
    """Test token refresh with a mocked token endpoint."""

    def test_refresh_success(self, client: TestClient):
        mock_response = httpx.Response(
            200,
            json={
                "access_token": "new-access-token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": "new-refresh-token",
            },
        )
        with patch("theridion_sidecar.api.oauth2.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_instance

            resp = client.post("/api/auth/oauth2/refresh", json={
                "token_url": "https://example.com/token",
                "refresh_token": "old-refresh-token",
                "client_id": "my-client",
                "client_secret": "my-secret",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "new-access-token"
        assert data["refresh_token"] == "new-refresh-token"
        assert data["expires_in"] == 3600

    def test_refresh_without_secret(self, client: TestClient):
        mock_response = httpx.Response(
            200,
            json={
                "access_token": "refreshed-token",
                "token_type": "Bearer",
                "expires_in": 1800,
            },
        )
        with patch("theridion_sidecar.api.oauth2.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_instance

            resp = client.post("/api/auth/oauth2/refresh", json={
                "token_url": "https://example.com/token",
                "refresh_token": "my-refresh-token",
                "client_id": "public-client",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "refreshed-token"

    def test_refresh_error(self, client: TestClient):
        mock_response = httpx.Response(
            401,
            json={"error": "invalid_grant"},
            text='{"error": "invalid_grant"}',
        )
        with patch("theridion_sidecar.api.oauth2.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_instance

            resp = client.post("/api/auth/oauth2/refresh", json={
                "token_url": "https://example.com/token",
                "refresh_token": "expired-token",
                "client_id": "my-client",
            })

        assert resp.status_code == 401
