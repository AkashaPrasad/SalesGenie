"""Security-focused tests — OWASP headers, auth enforcement, secret exposure."""

import pytest


class TestSecurityHeaders:
    """Verify OWASP-recommended headers are present on every response."""

    def test_x_content_type_options_present(self, client):
        """X-Content-Type-Options: nosniff must be set."""
        response = client.get("/")
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_deny(self, client):
        """X-Frame-Options: DENY must be set to prevent clickjacking."""
        response = client.get("/")
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_x_xss_protection_present(self, client):
        """X-XSS-Protection header must be set."""
        response = client.get("/")
        assert "X-XSS-Protection" in response.headers

    def test_strict_transport_security_present(self, client):
        """Strict-Transport-Security header must be present."""
        response = client.get("/")
        assert "Strict-Transport-Security" in response.headers
        assert "max-age" in response.headers["Strict-Transport-Security"]

    def test_referrer_policy_present(self, client):
        """Referrer-Policy header must be set."""
        response = client.get("/")
        assert "Referrer-Policy" in response.headers

    def test_permissions_policy_present(self, client):
        """Permissions-Policy header must restrict dangerous browser features."""
        response = client.get("/")
        assert "Permissions-Policy" in response.headers


class TestNoSecretsInResponses:
    """Verify that API responses never expose credentials or keys."""

    def test_gemini_key_not_in_response(self, client):
        """GEMINI_API_KEY value must not appear in any response body."""
        response = client.get("/")
        body = response.data.decode()
        assert "AIzaSy" not in body
        assert "GEMINI_API_KEY" not in body

    def test_client_secret_not_in_response(self, client):
        """OAuth client_secret must not appear in any response body."""
        response = client.get("/")
        assert b"client_secret" not in response.data

    def test_flask_secret_not_in_response(self, client):
        """Flask SECRET_KEY must not appear in any response body."""
        response = client.get("/")
        assert b"FLASK_SECRET_KEY" not in response.data


class TestOAuthSecurity:
    """Test OAuth2 CSRF protection via state parameter."""

    def test_callback_wrong_state_returns_403(self, client):
        """Mismatched state token must return 403 Forbidden."""
        with client.session_transaction() as sess:
            sess["oauth_state"] = "correct-secure-state"
        response = client.get(
            "/oauth2callback?state=attacker-injected-state&code=abc123"
        )
        assert response.status_code == 403

    def test_callback_no_state_in_session_returns_403(self, client):
        """Callback with no state in session must return 403."""
        response = client.get("/oauth2callback?state=some-state&code=abc123")
        assert response.status_code == 403

    def test_login_sets_state_in_session(self, client):
        """GET /login must store oauth_state in the session."""
        from unittest.mock import patch

        with patch(
            "routes.auth.get_auth_url",
            return_value="https://accounts.google.com?state=x",
        ):
            client.get("/login")
        with client.session_transaction() as sess:
            assert "oauth_state" in sess


class TestProtectedRoutes:
    """Verify all sensitive routes enforce authentication."""

    PROTECTED_ROUTES = [
        "/dashboard",
        "/leads",
        "/outreach",
    ]

    API_ROUTES_401 = [
        "/api/leads",
        "/api/dashboard/stats",
        "/api/dashboard/leads-by-stage",
    ]

    def test_protected_pages_redirect_unauthenticated(self, client):
        """All protected pages must redirect to login without a session."""
        for route in self.PROTECTED_ROUTES:
            response = client.get(route)
            assert response.status_code == 302, f"{route} did not redirect"
            assert "/login" in response.headers["Location"], f"{route} redirect wrong"

    def test_api_routes_return_401_unauthenticated(self, client):
        """All API routes must return 401 without authentication."""
        for route in self.API_ROUTES_401:
            response = client.get(route)
            assert response.status_code in (
                401,
                302,
            ), f"{route} should require auth, got {response.status_code}"
