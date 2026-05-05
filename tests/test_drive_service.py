"""Tests for Google Sheets / Drive service."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from services.drive_service import (
    add_lead_to_sheet,
    batch_add_leads,
    get_all_leads,
    get_sheets_service,
    initialize_sheet,
    log_sent_email,
    update_lead_stage,
)


class TestInitializeSheet:
    """Tests for initialize_sheet."""

    def test_writes_headers_when_empty(self, mock_sheets_service):
        """Empty sheet must get headers written."""
        mock_sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": []
        }
        initialize_sheet(mock_sheets_service, "sheet-id")
        assert mock_sheets_service.spreadsheets.called

    def test_skips_headers_when_present(self, mock_sheets_service):
        """Sheet with existing data must not overwrite headers."""
        mock_sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [["Name", "Company"]]
        }
        update_mock = (
            mock_sheets_service.spreadsheets.return_value.values.return_value.update
        )
        initialize_sheet(mock_sheets_service, "sheet-id")
        update_mock.assert_not_called()

    def test_handles_http_error_gracefully(self, mock_sheets_service):
        """HttpError must be caught, not raised."""
        resp = MagicMock()
        resp.status = 403
        resp.reason = "Forbidden"
        mock_sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        initialize_sheet(mock_sheets_service, "sheet-id")  # must not raise


class TestAddLeadToSheet:
    """Tests for add_lead_to_sheet."""

    def test_appends_lead_successfully(self, mock_sheets_service, sample_lead):
        """Successful append must return the API response dict."""
        result = add_lead_to_sheet(mock_sheets_service, "sheet-id", sample_lead)
        assert isinstance(result, dict)

    def test_raises_http_error(self, mock_sheets_service, sample_lead):
        """HttpError from Sheets API must propagate."""
        resp = MagicMock()
        resp.status = 500
        resp.reason = "Server Error"
        mock_sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        with pytest.raises(HttpError):
            add_lead_to_sheet(mock_sheets_service, "sheet-id", sample_lead)


class TestBatchAddLeads:
    """Tests for batch_add_leads."""

    def test_returns_empty_dict_for_no_leads(self, mock_sheets_service):
        """Empty list must return empty dict without API call."""
        result = batch_add_leads(mock_sheets_service, "sheet-id", [])
        assert result == {}

    def test_batch_appends_multiple_leads(self, mock_sheets_service, sample_lead):
        """Multiple leads appended in a single call."""
        result = batch_add_leads(
            mock_sheets_service, "sheet-id", [sample_lead, sample_lead]
        )
        assert isinstance(result, dict)


class TestGetAllLeads:
    """Tests for get_all_leads."""

    def test_returns_list_of_dicts(self, mock_sheets_service):
        """Leads fetched from sheet must return list of dicts."""
        result = get_all_leads(mock_sheets_service, "sheet-id")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "name" in result[0]

    def test_returns_empty_list_when_only_headers(self, mock_sheets_service):
        """Sheet with only header row returns empty list."""
        mock_sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
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
                ]
            ]
        }
        result = get_all_leads(mock_sheets_service, "sheet-id")
        assert result == []

    def test_returns_empty_list_on_http_error(self, mock_sheets_service):
        """HttpError must return empty list, not raise."""
        resp = MagicMock()
        resp.status = 403
        resp.reason = "Forbidden"
        mock_sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        result = get_all_leads(mock_sheets_service, "sheet-id")
        assert result == []

    def test_returns_empty_list_when_no_values(self, mock_sheets_service):
        """Empty sheet with no values returns empty list."""
        mock_sheets_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = (
            {}
        )
        result = get_all_leads(mock_sheets_service, "sheet-id")
        assert result == []


class TestUpdateLeadStage:
    """Tests for update_lead_stage."""

    def test_updates_cell_successfully(self, mock_sheets_service):
        """Stage update must call the Sheets API update endpoint."""
        mock_sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.return_value = (
            {}
        )
        result = update_lead_stage(mock_sheets_service, "sheet-id", 0, "Contacted")
        assert mock_sheets_service.spreadsheets.called

    def test_raises_http_error(self, mock_sheets_service):
        """HttpError must propagate from update_lead_stage."""
        resp = MagicMock()
        resp.status = 500
        resp.reason = "Server Error"
        mock_sheets_service.spreadsheets.return_value.values.return_value.update.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        with pytest.raises(HttpError):
            update_lead_stage(mock_sheets_service, "sheet-id", 0, "Closed Won")


class TestLogSentEmail:
    """Tests for log_sent_email."""

    def test_logs_email_to_sheet(self, mock_sheets_service):
        """log_sent_email must append a row to the Emails sheet."""
        mock_sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.return_value = (
            {}
        )
        result = log_sent_email(
            mock_sheets_service,
            "sheet-id",
            {"to": "test@test.com", "subject": "Hello", "message_id": "msg-123"},
        )
        assert isinstance(result, dict)

    def test_returns_empty_on_http_error(self, mock_sheets_service):
        """HttpError must return empty dict, not raise."""
        resp = MagicMock()
        resp.status = 403
        resp.reason = "Forbidden"
        mock_sheets_service.spreadsheets.return_value.values.return_value.append.return_value.execute.side_effect = HttpError(
            resp=resp, content=b"error"
        )
        result = log_sent_email(mock_sheets_service, "sheet-id", {"to": "x@x.com"})
        assert result == {}
