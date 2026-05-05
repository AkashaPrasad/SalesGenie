"""Tests for the lead scoring service."""

from unittest.mock import MagicMock, patch

import pytest

from services.lead_scorer import score_lead, validate_lead_for_scoring


class TestLeadScorer:
    """Unit tests for lead_scorer.score_lead."""

    def test_score_returns_integer_in_range(self, sample_lead):
        """Lead score must be an integer between 1 and 100."""
        with patch("services.gemini_service.model") as mock:
            mock.generate_content.return_value = MagicMock(text="72")
            score = score_lead(sample_lead)
        assert isinstance(score, int)
        assert 1 <= score <= 100

    def test_score_high_quality_lead(self, sample_lead):
        """High-value lead should score above 70 when Gemini says 88."""
        with patch("services.gemini_service.model") as mock:
            mock.generate_content.return_value = MagicMock(text="88")
            lead = {**sample_lead, "deal_size": 50000, "urgency": "high"}
            # Clear cache before test
            from services import gemini_service

            gemini_service._score_cache.clear()
            score = score_lead(lead)
        assert score > 70

    def test_empty_lead_raises_value_error(self):
        """Empty lead data must raise ValueError."""
        with pytest.raises(ValueError, match="Lead data cannot be empty"):
            score_lead({})

    def test_missing_email_raises_value_error(self):
        """Lead without email must raise ValueError."""
        with pytest.raises(ValueError, match="email"):
            score_lead({"name": "Test", "company": "Co"})

    def test_gemini_timeout_returns_default_score(self, sample_lead):
        """API TimeoutError must return fallback score of 50."""
        with patch("services.gemini_service.model") as mock:
            mock.generate_content.side_effect = TimeoutError("API timeout")
            from services import gemini_service

            gemini_service._score_cache.clear()
            score = score_lead({**sample_lead, "email": "timeout@test.com"})
        assert score == 50

    def test_gemini_generic_error_returns_default(self, sample_lead):
        """Any unexpected exception must return fallback score of 50."""
        with patch("services.gemini_service.model") as mock:
            mock.generate_content.side_effect = RuntimeError("Unknown error")
            from services import gemini_service

            gemini_service._score_cache.clear()
            score = score_lead({**sample_lead, "email": "error@test.com"})
        assert score == 50

    def test_score_clamped_above_100(self, sample_lead):
        """Score > 100 returned by Gemini must be clamped to 100."""
        with patch("services.gemini_service.model") as mock:
            mock.generate_content.return_value = MagicMock(text="150")
            from services import gemini_service

            gemini_service._score_cache.clear()
            score = score_lead({**sample_lead, "email": "clamp-high@test.com"})
        assert score == 100

    def test_score_clamped_below_1(self, sample_lead):
        """Score < 1 returned by Gemini must be clamped to 1."""
        with patch("services.gemini_service.model") as mock:
            mock.generate_content.return_value = MagicMock(text="-5")
            from services import gemini_service

            gemini_service._score_cache.clear()
            score = score_lead({**sample_lead, "email": "clamp-low@test.com"})
        assert score == 1


class TestValidateLeadForScoring:
    """Tests for validate_lead_for_scoring helper."""

    def test_valid_lead_returns_true(self, sample_lead):
        assert validate_lead_for_scoring(sample_lead) is True

    def test_missing_name_returns_false(self, sample_lead):
        lead = {**sample_lead, "name": ""}
        assert validate_lead_for_scoring(lead) is False

    def test_missing_email_returns_false(self, sample_lead):
        lead = {**sample_lead, "email": ""}
        assert validate_lead_for_scoring(lead) is False

    def test_missing_company_returns_false(self, sample_lead):
        lead = {**sample_lead, "company": ""}
        assert validate_lead_for_scoring(lead) is False
