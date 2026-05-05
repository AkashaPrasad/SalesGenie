"""Pytest fixtures shared across all test modules."""

import os
from unittest.mock import MagicMock, patch

import pytest

# Set env vars before any imports so Config reads them
os.environ.update(
    {
        "GEMINI_API_KEY": "test-gemini-key-not-real",
        "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "FLASK_SECRET_KEY": "test-flask-secret-key-32-chars-long",
        "REDIRECT_URI": "http://localhost:5000/oauth2callback",
        "SPREADSHEET_ID": "test-spreadsheet-id-123",
    }
)


@pytest.fixture
def app():
    """Create a test Flask app with safe overrides."""
    with (
        patch("google.generativeai.configure"),
        patch("google.generativeai.GenerativeModel"),
    ):
        from app import create_app

        application = create_app(
            {
                "TESTING": True,
                "GEMINI_API_KEY": "test-gemini-key-not-real",
                "GOOGLE_CLIENT_ID": "test-client-id",
                "GOOGLE_CLIENT_SECRET": "test-secret",
                "FLASK_SECRET_KEY": "test-flask-secret-key-32-chars-long",
                "SPREADSHEET_ID": "test-sheet-id",
                "SESSION_COOKIE_SECURE": False,
            }
        )
        yield application


@pytest.fixture
def client(app):
    """HTTP test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client with a pre-authenticated session."""
    with client.session_transaction() as sess:
        sess["user_email"] = "test@example.com"
        sess["user_name"] = "Test User"
        sess["credentials"] = {
            "token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/gmail.send"],
        }
    return client


@pytest.fixture
def sample_lead():
    """Standard test lead fixture."""
    return {
        "name": "John Smith",
        "company": "Acme Corp",
        "email": "john@acme.com",
        "deal_size": 5000,
        "stage": "Prospecting",
        "urgency": "medium",
        "product": "SalesGenie Pro",
        "notes": "",
    }


@pytest.fixture
def mock_gemini_model():
    """Mock Gemini model that returns predictable responses."""
    with patch("services.gemini_service.model") as mock:
        mock.generate_content.return_value = MagicMock(text="75")
        yield mock


@pytest.fixture
def mock_sheets_service():
    """Mock Google Sheets service."""
    mock = MagicMock()
    mock.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
        "values": [
            [
                "Name",
                "Company",
                "Email",
                "Deal Size",
                "Stage",
                "Score",
                "Urgency",
                "Product",
                "Notes",
                "Created At",
            ],
            [
                "John Smith",
                "Acme Corp",
                "john@acme.com",
                "5000",
                "Prospecting",
                "72",
                "medium",
                "SalesGenie",
                "",
                "2026-05-05",
            ],
        ]
    }
    mock.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = {
        "updates": {"updatedRows": 1}
    }
    return mock


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service."""
    mock = MagicMock()
    mock.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "msg-123",
        "threadId": "thread-456",
    }
    return mock


@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar service."""
    mock = MagicMock()
    mock.events.return_value.insert.return_value.execute.return_value = {
        "id": "event-789",
        "htmlLink": "https://calendar.google.com/event/789",
    }
    return mock
