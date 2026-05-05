"""Lead scoring module — thin wrapper that validates before calling Gemini."""

import logging

from services.gemini_service import score_lead as _gemini_score_lead

logger = logging.getLogger(__name__)


def score_lead(lead_data: dict) -> int:
    """Validate and score a lead using Gemini AI.

    Args:
        lead_data: Dict containing lead name, company, email, deal_size, urgency.

    Returns:
        Integer score between 1 and 100.

    Raises:
        ValueError: If lead_data is missing required fields.
    """
    if not lead_data:
        raise ValueError("Lead data cannot be empty")
    if not lead_data.get("email"):
        raise ValueError("Lead must have an email address")

    score = _gemini_score_lead(lead_data)
    logger.info(
        "Lead scored: email=%s score=%d",
        lead_data.get("email"),
        score,
    )
    return score


def validate_lead_for_scoring(lead_data: dict) -> bool:
    """Check whether a lead has the minimum fields needed for scoring.

    Args:
        lead_data: Dict with lead fields.

    Returns:
        True if scoreable, False otherwise.
    """
    required = ["name", "company", "email"]
    return all(lead_data.get(f) for f in required)
