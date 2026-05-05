"""Tests for the Lead data model."""

import pytest

from models.lead import Lead, validate_lead_input


class TestLeadModel:
    """Unit tests for the Lead dataclass."""

    def test_lead_to_dict_round_trip(self, sample_lead):
        """Lead.to_dict() then Lead.from_dict() must reconstruct the same data."""
        lead = Lead.from_dict(sample_lead)
        d = lead.to_dict()
        rebuilt = Lead.from_dict(d)
        assert rebuilt.name == lead.name
        assert rebuilt.email == lead.email
        assert rebuilt.deal_size == lead.deal_size

    def test_lead_defaults(self):
        """Lead created with minimal fields must have sensible defaults."""
        lead = Lead(name="Test", company="Co", email="t@co.com")
        assert lead.stage == "Prospecting"
        assert lead.urgency == "medium"
        assert lead.score == 50
        assert lead.notes == ""

    def test_from_sheet_row(self):
        """from_sheet_row must map row values to correct fields."""
        headers = [
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
        row = [
            "Jane",
            "Acme",
            "jane@acme.com",
            "5000",
            "Contacted",
            "80",
            "high",
            "Pro",
            "VIP",
            "2026-05-05",
        ]
        lead = Lead.from_sheet_row(headers, row)
        assert lead.name == "Jane"
        assert lead.score == 80
        assert lead.stage == "Contacted"

    def test_from_sheet_row_short_row(self):
        """Rows shorter than headers must be padded safely."""
        headers = [
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
        row = ["Jane", "Acme"]
        lead = Lead.from_sheet_row(headers, row)
        assert lead.name == "Jane"
        assert lead.email == ""


class TestValidateLeadInput:
    """Tests for validate_lead_input helper."""

    def test_valid_input_returns_true(self, sample_lead):
        """Valid lead data must return (True, '')."""
        is_valid, error = validate_lead_input(sample_lead)
        assert is_valid is True
        assert error == ""

    def test_short_name_fails(self):
        """Single-char name must fail validation."""
        is_valid, error = validate_lead_input(
            {"name": "A", "email": "a@b.com", "company": "Co"}
        )
        assert is_valid is False
        assert "Name" in error or "name" in error

    def test_missing_email_fails(self):
        """Missing email must fail validation."""
        is_valid, error = validate_lead_input({"name": "Test User", "company": "Co"})
        assert is_valid is False
        assert "email" in error.lower()

    def test_invalid_email_format_fails(self):
        """Email without @ must fail validation."""
        is_valid, error = validate_lead_input(
            {"name": "Test", "email": "notanemail", "company": "Co"}
        )
        assert is_valid is False

    def test_missing_company_fails(self):
        """Missing company must fail validation."""
        is_valid, error = validate_lead_input(
            {"name": "Test User", "email": "t@test.com"}
        )
        assert is_valid is False

    def test_invalid_stage_fails(self):
        """Invalid pipeline stage must fail validation."""
        is_valid, error = validate_lead_input(
            {
                "name": "Test User",
                "email": "t@test.com",
                "company": "Co",
                "stage": "InvalidStage",
            }
        )
        assert is_valid is False

    def test_invalid_deal_size_fails(self):
        """Non-numeric deal_size must fail validation."""
        is_valid, error = validate_lead_input(
            {
                "name": "Test User",
                "email": "t@test.com",
                "company": "Co",
                "deal_size": "abc",
            }
        )
        assert is_valid is False

    def test_invalid_urgency_fails(self):
        """Invalid urgency value must fail validation."""
        is_valid, error = validate_lead_input(
            {
                "name": "Test User",
                "email": "t@test.com",
                "company": "Co",
                "urgency": "extreme",
            }
        )
        assert is_valid is False
