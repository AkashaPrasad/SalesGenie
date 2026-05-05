"""Integration-style tests for authenticated API routes using mocked Google services."""

from unittest.mock import MagicMock, patch

import pytest


class TestDashboardStatsAPI:
    """Tests for GET /api/dashboard/stats with mocked Sheets."""

    def test_stats_returns_200_with_valid_session(self, auth_client):
        """Authenticated request must return 200 with stats dict."""
        with (
            patch("routes.dashboard._get_credentials") as mock_creds,
            patch("routes.dashboard.get_sheets_service") as mock_svc,
            patch("routes.dashboard.get_all_leads") as mock_leads,
        ):
            mock_creds.return_value = MagicMock()
            mock_svc.return_value = MagicMock()
            mock_leads.return_value = [
                {
                    "name": "A",
                    "company": "Co",
                    "email": "a@co.com",
                    "deal_size": "5000",
                    "stage": "Closed Won",
                    "score": "80",
                    "urgency": "high",
                    "product": "",
                    "notes": "",
                    "created_at": "",
                }
            ]
            response = auth_client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_leads" in data
        assert data["total_leads"] == 1

    def test_stats_returns_zeros_for_empty_sheet(self, auth_client):
        """Empty lead list must return zero stats."""
        with (
            patch("routes.dashboard._get_credentials") as mock_creds,
            patch("routes.dashboard.get_sheets_service"),
            patch("routes.dashboard.get_all_leads", return_value=[]),
        ):
            mock_creds.return_value = MagicMock()
            response = auth_client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_leads"] == 0
        assert data["win_rate"] == 0


class TestLeadsByStageAPI:
    """Tests for GET /api/dashboard/leads-by-stage."""

    def test_returns_grouped_stages(self, auth_client):
        """Response must include all pipeline stages as keys."""
        sample_leads = [
            {
                "name": "A",
                "company": "X",
                "email": "a@x.com",
                "deal_size": "1000",
                "stage": "Prospecting",
                "score": "60",
                "urgency": "medium",
                "product": "",
                "notes": "",
                "created_at": "",
            }
        ]
        with (
            patch("routes.dashboard._get_credentials") as mock_creds,
            patch("routes.dashboard.get_sheets_service"),
            patch("routes.dashboard.get_all_leads", return_value=sample_leads),
        ):
            mock_creds.return_value = MagicMock()
            response = auth_client.get("/api/dashboard/leads-by-stage")
        assert response.status_code == 200
        data = response.get_json()
        assert "stages" in data
        assert "Prospecting" in data["stages"]


class TestGetLeadsAPI:
    """Tests for GET /api/leads with mocked Sheets."""

    def test_get_leads_returns_list(self, auth_client):
        """Authenticated GET /api/leads must return leads list."""
        mock_leads = [
            {
                "name": "B",
                "email": "b@co.com",
                "company": "Co",
                "deal_size": "2000",
                "stage": "Contacted",
                "score": "55",
                "urgency": "low",
                "product": "",
                "notes": "",
                "created_at": "",
            }
        ]
        with (
            patch("routes.leads._require_auth") as mock_auth,
            patch("routes.leads.get_sheets_service"),
            patch("routes.leads.get_all_leads", return_value=mock_leads),
        ):
            mock_auth.return_value = MagicMock()
            response = auth_client.get("/api/leads")
        assert response.status_code == 200
        data = response.get_json()
        assert "leads" in data
        assert data["count"] == 1


class TestSearchLeadsAPI:
    """Tests for GET /api/leads/search."""

    def test_search_returns_filtered_results(self, auth_client):
        """Search with matching query must return filtered leads."""
        all_leads = [
            {
                "name": "Alice Wonder",
                "email": "alice@co.com",
                "company": "Wonder Inc",
                "deal_size": "3000",
                "stage": "Proposal",
                "score": "70",
                "urgency": "high",
                "product": "",
                "notes": "",
                "created_at": "",
            },
            {
                "name": "Bob Builder",
                "email": "bob@build.com",
                "company": "Build Co",
                "deal_size": "1000",
                "stage": "Prospecting",
                "score": "40",
                "urgency": "low",
                "product": "",
                "notes": "",
                "created_at": "",
            },
        ]
        with (
            patch("routes.leads._require_auth") as mock_auth,
            patch("routes.leads.get_sheets_service"),
            patch("routes.leads.get_all_leads", return_value=all_leads),
        ):
            mock_auth.return_value = MagicMock()
            response = auth_client.get("/api/leads/search?q=alice")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["leads"]) == 1
        assert data["leads"][0]["name"] == "Alice Wonder"

    def test_search_empty_query_returns_all(self, auth_client):
        """Empty search query must return all leads."""
        all_leads = [
            {
                "name": "A",
                "email": "a@x.com",
                "company": "X",
                "deal_size": "0",
                "stage": "Prospecting",
                "score": "50",
                "urgency": "medium",
                "product": "",
                "notes": "",
                "created_at": "",
            }
        ]
        with (
            patch("routes.leads._require_auth") as mock_auth,
            patch("routes.leads.get_sheets_service"),
            patch("routes.leads.get_all_leads", return_value=all_leads),
        ):
            mock_auth.return_value = MagicMock()
            response = auth_client.get("/api/leads/search")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["leads"]) == 1


class TestUpdateStageAPI:
    """Tests for PATCH /api/leads/<row_index>/stage."""

    def test_update_stage_success(self, auth_client):
        """Valid stage update must return 200."""
        with (
            patch("routes.leads._require_auth") as mock_auth,
            patch("routes.leads.get_sheets_service"),
            patch("routes.leads.update_lead_stage"),
        ):
            mock_auth.return_value = MagicMock()
            response = auth_client.patch(
                "/api/leads/0/stage",
                json={"stage": "Contacted"},
                content_type="application/json",
            )
        assert response.status_code == 200

    def test_update_stage_missing_stage_field(self, auth_client):
        """PATCH without stage field must return 400."""
        with patch("routes.leads._require_auth") as mock_auth:
            mock_auth.return_value = MagicMock()
            response = auth_client.patch(
                "/api/leads/0/stage",
                json={},
                content_type="application/json",
            )
        assert response.status_code == 400


class TestGenerateEmailAPI:
    """Tests for POST /api/outreach/generate (authenticated)."""

    def test_generate_email_authenticated(self, auth_client):
        """Authenticated generate request must return email_draft."""
        with (
            patch("routes.outreach._get_credentials") as mock_creds,
            patch(
                "routes.outreach.generate_email_draft",
                return_value="Subject: Hello\n\nDear Jane, test body here.",
            ),
            patch(
                "routes.outreach.analyze_email", return_value={"persuasion_score": 75}
            ),
        ):
            mock_creds.return_value = MagicMock()
            response = auth_client.post(
                "/api/outreach/generate",
                json={
                    "lead_name": "Jane",
                    "company": "Acme",
                    "lead_email": "jane@acme.com",
                    "product": "Pro",
                    "deal_size": 5000,
                    "tone": "professional",
                },
                content_type="application/json",
            )
        assert response.status_code == 200
        data = response.get_json()
        assert "email_draft" in data


class TestAuthService:
    """Tests for auth_service helper functions."""

    def test_credentials_to_dict_includes_token(self):
        """credentials_to_dict must include token key."""
        from services.auth_service import credentials_to_dict

        mock_cred = MagicMock()
        mock_cred.token = "access-token-abc"
        mock_cred.refresh_token = "refresh-token-xyz"
        mock_cred.token_uri = "https://oauth2.googleapis.com/token"
        mock_cred.scopes = ["https://www.googleapis.com/auth/gmail.send"]

        result = credentials_to_dict(mock_cred)
        assert result["token"] == "access-token-abc"
        assert "refresh_token" in result
        assert "scopes" in result

    def test_dict_to_credentials_creates_credentials(self):
        """dict_to_credentials must return a Credentials object."""
        from services.auth_service import dict_to_credentials

        cred_dict = {
            "token": "tok",
            "refresh_token": "ref",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/gmail.send"],
        }
        result = dict_to_credentials(cred_dict)
        assert result.token == "tok"
        assert result.refresh_token == "ref"

    def test_get_auth_url_returns_google_url(self):
        """get_auth_url must return a URL pointing to Google OAuth."""
        from services.auth_service import get_auth_url

        url = get_auth_url("test-state-token")
        assert "accounts.google.com" in url
        assert "test-state-token" in url

    def test_validate_lead_for_scoring_full(self):
        """validate_lead_for_scoring must return True for a complete lead."""
        from services.lead_scorer import validate_lead_for_scoring

        assert (
            validate_lead_for_scoring({"name": "A", "company": "B", "email": "a@b.com"})
            is True
        )
