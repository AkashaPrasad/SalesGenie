"""Tests for Google Calendar service."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from services.calendar_service import list_upcoming_followups, schedule_followup


class TestScheduleFollowup:
    """Tests for schedule_followup."""

    def test_creates_event_successfully(self, mock_calendar_service):
        """schedule_followup must return event dict with id and htmlLink."""
        result = schedule_followup(
            mock_calendar_service,
            "Jane Smith",
            "jane@acme.com",
            datetime(2026, 6, 1, 10, 0),
            "Discuss Q3 proposal",
        )
        assert "id" in result
        assert result["id"] == "event-789"

    def test_event_title_includes_lead_name(self, mock_calendar_service):
        """Calendar event must be created with lead name in title."""
        schedule_followup(
            mock_calendar_service,
            "Bob Jones",
            "bob@corp.com",
            datetime(2026, 6, 1, 10, 0),
        )
        call_args = mock_calendar_service.events.return_value.insert.call_args
        event_body = call_args[1]["body"]
        assert "Bob Jones" in event_body["summary"]

    def test_raises_http_error(self, mock_calendar_service):
        """HttpError from Calendar API must propagate."""
        resp = MagicMock()
        resp.status = 403
        resp.reason = "Forbidden"
        mock_calendar_service.events.return_value.insert.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        with pytest.raises(HttpError):
            schedule_followup(
                mock_calendar_service,
                "Test",
                "test@test.com",
                datetime(2026, 6, 1, 10, 0),
            )


class TestListUpcomingFollowups:
    """Tests for list_upcoming_followups."""

    def test_returns_list_of_events(self, mock_calendar_service):
        """Returns list of upcoming events."""
        mock_calendar_service.events.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "e1", "summary": "Follow up — SalesGenie"}]
        }
        result = list_upcoming_followups(mock_calendar_service)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_returns_empty_list_on_error(self, mock_calendar_service):
        """HttpError must return empty list, not raise."""
        resp = MagicMock()
        resp.status = 403
        resp.reason = "Forbidden"
        mock_calendar_service.events.return_value.list.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        result = list_upcoming_followups(mock_calendar_service)
        assert result == []
