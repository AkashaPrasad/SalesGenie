"""Tests for the Gemini AI service."""

import json
from unittest.mock import MagicMock, patch

import pytest

from services.gemini_service import (
    analyze_email,
    generate_email_draft,
    generate_followup_sequence,
    get_followup_timing,
    handle_objection,
    score_lead,
)
from services import gemini_service


class TestGenerateEmailDraft:
    """Tests for generate_email_draft."""

    def test_returns_non_empty_string(self, sample_lead):
        """Email draft must be a non-empty string."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.return_value = MagicMock(
                text="Subject: Hello\n\nDear John, this is a test email body."
            )
            result = generate_email_draft(sample_lead, tone="professional")
        assert isinstance(result, str)
        assert len(result) > 20

    def test_handles_api_error_with_fallback(self, sample_lead):
        """API error must return a fallback email, not raise."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.side_effect = Exception("API Error")
            result = generate_email_draft(sample_lead, tone="professional")
        assert result is not None
        assert "John Smith" in result or "there" in result

    def test_different_tones_accepted(self, sample_lead):
        """All supported tones must not raise exceptions."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.return_value = MagicMock(text="Subject: Hi\n\nBody")
            for tone in ["professional", "friendly", "urgent", "formal"]:
                result = generate_email_draft(sample_lead, tone=tone)
                assert isinstance(result, str)


class TestAnalyzeEmail:
    """Tests for analyze_email."""

    def test_returns_dict_with_score(self):
        """Analysis must return a dict with persuasion_score."""
        valid_json = json.dumps(
            {
                "persuasion_score": 78,
                "strengths": ["Clear CTA"],
                "improvements": ["Add urgency"],
                "predicted_response_rate": "22%",
            }
        )
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.return_value = MagicMock(text=valid_json)
            result = analyze_email("Dear John, test email.")
        assert isinstance(result, dict)
        assert result["persuasion_score"] == 78

    def test_handles_invalid_json_gracefully(self):
        """Non-JSON response must return a default dict, not raise."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.return_value = MagicMock(text="not json at all")
            result = analyze_email("test email")
        assert "persuasion_score" in result
        assert isinstance(result["persuasion_score"], int)

    def test_handles_api_error_gracefully(self):
        """API error must return a fallback dict."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.side_effect = Exception("timeout")
            result = analyze_email("test email")
        assert "persuasion_score" in result


class TestScoreLeadGemini:
    """Tests for the core score_lead function in gemini_service."""

    def test_clamps_score_above_100(self):
        """Score > 100 must be clamped to 100."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.return_value = MagicMock(text="200")
            gemini_service._score_cache.clear()
            result = score_lead(
                {
                    "name": "A",
                    "company": "B",
                    "email": "clamp@test.com",
                    "deal_size": 0,
                    "urgency": "low",
                    "product": "",
                }
            )
        assert result == 100

    def test_non_numeric_gemini_returns_50(self):
        """Non-numeric Gemini response must fall back to 50."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.return_value = MagicMock(text="definitely-high")
            gemini_service._score_cache.clear()
            result = score_lead(
                {
                    "name": "A",
                    "company": "B",
                    "email": "nonnumeric@test.com",
                    "deal_size": 0,
                    "urgency": "low",
                    "product": "",
                }
            )
        assert result == 50


class TestGetFollowupTiming:
    """Tests for get_followup_timing."""

    def test_returns_int_in_range(self):
        """Follow-up timing must be between 1 and 14 days."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.return_value = MagicMock(text="3")
            result = get_followup_timing("medium")
        assert isinstance(result, int)
        assert 1 <= result <= 14

    def test_error_returns_default_by_urgency(self):
        """API error must return a sensible default per urgency level."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.side_effect = Exception("fail")
            assert get_followup_timing("high") == 1
            assert get_followup_timing("medium") == 3
            assert get_followup_timing("low") == 7


class TestHandleObjection:
    """Tests for handle_objection."""

    def test_returns_list_of_responses(self):
        """Must return a list with response dicts."""
        valid_json = json.dumps([{"response": "Great question. Our value..."}])
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.return_value = MagicMock(text=valid_json)
            result = handle_objection("Your price is too high.")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "response" in result[0]

    def test_handles_api_error_gracefully(self):
        """API error must return fallback list, not raise."""
        with patch.object(gemini_service, "model") as mock:
            mock.generate_content.side_effect = Exception("fail")
            result = handle_objection("objection text")
        assert isinstance(result, list)
        assert len(result) >= 1
