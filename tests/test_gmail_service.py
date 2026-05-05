"""Tests for the Gmail API service."""

from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from services.gmail_service import get_user_profile, list_recent_emails, send_email


class TestSendEmail:
    """Tests for send_email."""

    def test_send_returns_message_id(self, mock_gmail_service):
        """Successful send must return a dict with message ID."""
        result = send_email(mock_gmail_service, "to@test.com", "Hello", "Body text")
        assert "id" in result
        assert result["id"] == "msg-123"

    def test_send_calls_gmail_api(self, mock_gmail_service):
        """send_email must call the Gmail users.messages.send endpoint."""
        send_email(mock_gmail_service, "to@test.com", "Subj", "Body")
        assert mock_gmail_service.users.called

    def test_send_raises_on_http_error(self, mock_gmail_service):
        """HttpError from Gmail API must propagate, not be silenced."""
        resp = MagicMock()
        resp.status = 403
        resp.reason = "Forbidden"
        mock_gmail_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"Forbidden"
        )
        with pytest.raises(HttpError):
            send_email(mock_gmail_service, "to@test.com", "Subj", "Body")


class TestListRecentEmails:
    """Tests for list_recent_emails."""

    def test_returns_list_on_success(self, mock_gmail_service):
        """Returns list of message dicts."""
        mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [{"id": "1"}, {"id": "2"}]
        }
        result = list_recent_emails(mock_gmail_service)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_returns_empty_list_on_error(self, mock_gmail_service):
        """HTTP error must return empty list, not raise."""
        resp = MagicMock()
        resp.status = 500
        resp.reason = "Server Error"
        mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        result = list_recent_emails(mock_gmail_service)
        assert result == []


class TestGetUserProfile:
    """Tests for get_user_profile."""

    def test_returns_dict_on_success(self, mock_gmail_service):
        """Returns profile dict."""
        mock_gmail_service.users.return_value.getProfile.return_value.execute.return_value = {
            "emailAddress": "user@test.com"
        }
        result = get_user_profile(mock_gmail_service)
        assert result.get("emailAddress") == "user@test.com"

    def test_returns_empty_dict_on_error(self, mock_gmail_service):
        """HTTP error must return empty dict."""
        resp = MagicMock()
        resp.status = 403
        resp.reason = "Forbidden"
        mock_gmail_service.users.return_value.getProfile.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        result = get_user_profile(mock_gmail_service)
        assert result == {}
