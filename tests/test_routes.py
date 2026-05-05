"""Tests for Flask route blueprints."""

from unittest.mock import MagicMock, patch

import pytest


class TestIndexRoute:
    """Tests for the landing page."""

    def test_index_returns_200(self, client):
        """Landing page must return 200 for unauthenticated visitors."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_contains_sign_in(self, client):
        """Landing page must have a sign-in link."""
        response = client.get("/")
        assert b"Sign in" in response.data or b"login" in response.data.lower()


class TestDashboardRoutes:
    """Tests for dashboard routes."""

    def test_dashboard_requires_auth(self, client):
        """Unauthenticated requests to /dashboard must redirect to login."""
        response = client.get("/dashboard")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_dashboard_loads_for_auth_user(self, auth_client):
        """Authenticated users must get a 200 from /dashboard."""
        with (
            patch("routes.dashboard._get_credentials") as mock_creds,
            patch("routes.dashboard._ensure_sheet_initialized"),
        ):
            mock_creds.return_value = MagicMock()
            response = auth_client.get("/dashboard")
        assert response.status_code == 200

    def test_stats_requires_auth(self, client):
        """Stats API must reject unauthenticated requests."""
        response = client.get("/api/dashboard/stats")
        assert response.status_code in (302, 401)

    def test_leads_by_stage_requires_auth(self, client):
        """Leads-by-stage API must reject unauthenticated requests."""
        response = client.get("/api/dashboard/leads-by-stage")
        assert response.status_code in (302, 401)


class TestLeadRoutes:
    """Tests for lead CRUD routes."""

    def test_leads_page_requires_auth(self, client):
        """Unauthenticated /leads page must redirect."""
        response = client.get("/leads")
        assert response.status_code == 302

    def test_get_leads_api_requires_auth(self, client):
        """GET /api/leads must return 401 without session."""
        response = client.get("/api/leads")
        assert response.status_code == 401

    def test_create_lead_missing_email(self, auth_client):
        """POST /api/leads without email must return 400."""
        with patch("routes.leads._require_auth") as mock_auth:
            mock_auth.return_value = MagicMock()
            response = auth_client.post(
                "/api/leads",
                json={"name": "Test User", "company": "Co"},
                content_type="application/json",
            )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_create_lead_invalid_email(self, auth_client):
        """POST /api/leads with malformed email must return 400."""
        with patch("routes.leads._require_auth") as mock_auth:
            mock_auth.return_value = MagicMock()
            response = auth_client.post(
                "/api/leads",
                json={"name": "Test", "email": "not-an-email", "company": "Co"},
                content_type="application/json",
            )
        assert response.status_code == 400

    def test_create_lead_missing_name(self, auth_client):
        """POST /api/leads without name must return 400."""
        with patch("routes.leads._require_auth") as mock_auth:
            mock_auth.return_value = MagicMock()
            response = auth_client.post(
                "/api/leads",
                json={"email": "test@test.com", "company": "Co"},
                content_type="application/json",
            )
        assert response.status_code == 400

    def test_create_lead_valid_data(self, auth_client, sample_lead):
        """POST /api/leads with valid data must return 201."""
        with (
            patch("routes.leads._require_auth") as mock_auth,
            patch("routes.leads.add_lead_to_sheet"),
            patch("routes.leads.score_lead", return_value=72),
        ):
            mock_auth.return_value = MagicMock()
            with patch("routes.leads.get_sheets_service"):
                response = auth_client.post(
                    "/api/leads",
                    json=sample_lead,
                    content_type="application/json",
                )
        assert response.status_code == 201
        data = response.get_json()
        assert "lead" in data

    def test_create_lead_no_json_body(self, auth_client):
        """POST /api/leads without JSON body must return 400."""
        with patch("routes.leads._require_auth") as mock_auth:
            mock_auth.return_value = MagicMock()
            response = auth_client.post("/api/leads", data="not json")
        assert response.status_code == 400


class TestOutreachRoutes:
    """Tests for outreach routes."""

    def test_outreach_page_requires_auth(self, client):
        """Unauthenticated /outreach page must redirect."""
        response = client.get("/outreach")
        assert response.status_code == 302

    def test_generate_email_requires_auth(self, client):
        """POST /api/outreach/generate must return 401 without session."""
        response = client.post("/api/outreach/generate", json={"lead_name": "X"})
        assert response.status_code == 401

    def test_generate_email_missing_name(self, auth_client):
        """POST with empty lead_name must return 400."""
        response = auth_client.post(
            "/api/outreach/generate",
            json={"lead_name": ""},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_send_email_requires_auth(self, client):
        """POST /api/outreach/send must return 401 without session."""
        response = client.post("/api/outreach/send", json={})
        assert response.status_code == 401

    def test_schedule_followup_requires_auth(self, client):
        """POST /api/outreach/schedule-followup must return 401 without session."""
        response = client.post("/api/outreach/schedule-followup", json={})
        assert response.status_code == 401


class TestAuthRoutes:
    """Tests for auth routes."""

    def test_login_redirects_to_google(self, client):
        """GET /login must redirect to Google OAuth2."""
        with patch(
            "routes.auth.get_auth_url",
            return_value="https://accounts.google.com/o/oauth2/auth?x=1",
        ):
            response = client.get("/login")
        assert response.status_code == 302
        assert "google.com" in response.headers["Location"]

    def test_logout_clears_session(self, auth_client):
        """GET /logout must clear session and redirect to index."""
        response = auth_client.get("/logout")
        assert response.status_code == 302
        with auth_client.session_transaction() as sess:
            assert "user_email" not in sess

    def test_oauth_callback_wrong_state(self, client):
        """Callback with tampered state must return 403."""
        with client.session_transaction() as sess:
            sess["oauth_state"] = "correct-state-value"
        response = client.get("/oauth2callback?state=tampered-state&code=authcode123")
        assert response.status_code == 403

    def test_oauth_callback_missing_code(self, client):
        """Callback with matching state but no code must return 400."""
        with client.session_transaction() as sess:
            sess["oauth_state"] = "valid-state"
        response = client.get("/oauth2callback?state=valid-state")
        assert response.status_code == 400
