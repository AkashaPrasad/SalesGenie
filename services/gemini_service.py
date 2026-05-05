"""Google Gemini AI service for lead scoring, email drafting, and coaching."""

import json
import logging

import google.generativeai as genai

from config import Config

logger = logging.getLogger(__name__)

genai.configure(api_key=Config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

SCORE_PROMPT = (
    "You are a sales expert. Score this lead 1-100 (100 = perfect lead).\n"
    "Reply with ONLY a number, nothing else.\n"
    "Lead: Name={name}, Company={company}, Deal size=${deal_size}, "
    "Urgency={urgency}, Product={product}"
)

EMAIL_PROMPT = (
    "You are an expert sales copywriter specializing in persuasion psychology.\n"
    "Write a personalized outreach email for:\n"
    "- Lead: {name} at {company}\n"
    "- Product: {product}\n"
    "- Tone: {tone}\n"
    "- Deal size context: ${deal_size}\n\n"
    "Include: compelling subject line, personalized opener, clear value "
    "proposition, and a specific CTA.\n"
    "Format exactly as:\nSubject: [subject line]\n\n[email body]"
)

COACH_PROMPT = (
    "Analyze this sales email. Reply ONLY with valid JSON (no markdown):\n"
    '{{"persuasion_score": 1-100, "strengths": ["s1","s2","s3"], '
    '"improvements": ["i1","i2","i3"], "predicted_response_rate": "X%"}}\n\n'
    "Email:\n{email_content}"
)

FOLLOWUP_PROMPT = (
    "You are a sales expert. Recommend a follow-up timeline for a {urgency} urgency lead.\n"
    "Reply with ONLY a number (days until follow-up, between 1 and 14)."
)

SEQUENCE_PROMPT = (
    "Generate a 3-email follow-up sequence for {name} at {company} "
    "interested in {product}. Tone: {tone}.\n"
    "Format as JSON: "
    '[{{"day": 1, "subject": "...", "body": "..."}}, ...]'
)

OBJECTION_PROMPT = (
    "You are a sales coach. The prospect said: '{objection}'\n"
    "Give 3 concise, professional counter-responses. "
    "Reply as JSON: [{{'response': '...'}}]"
)

_score_cache: dict = {}


def score_lead(lead_data: dict) -> int:
    """Score a lead using Gemini AI (1-100).

    Args:
        lead_data: Dict with name, company, email, deal_size, urgency, product.

    Returns:
        Integer quality score between 1 and 100.

    Raises:
        ValueError: If lead_data is empty or missing email.
    """
    if not lead_data:
        raise ValueError("Lead data cannot be empty")
    if not lead_data.get("email"):
        raise ValueError("Lead must have an email address")

    cache_key = f"{lead_data.get('email')}:{lead_data.get('deal_size')}"
    if cache_key in _score_cache:
        return _score_cache[cache_key]

    try:
        prompt = SCORE_PROMPT.format(
            name=lead_data.get("name", ""),
            company=lead_data.get("company", ""),
            deal_size=lead_data.get("deal_size", 0),
            urgency=lead_data.get("urgency", "medium"),
            product=lead_data.get("product", ""),
        )
        response = model.generate_content(prompt)
        raw = response.text.strip()
        score = max(1, min(100, int(raw)))
        _score_cache[cache_key] = score
        logger.info("Lead scored: score=%d for %s", score, lead_data.get("email"))
        return score
    except (ValueError, AttributeError):
        logger.warning("Gemini returned non-numeric score, using default 50")
        return 50
    except TimeoutError as e:
        logger.error("Gemini score_lead timeout: %s", str(e))
        return 50
    except Exception as e:
        logger.error("Gemini score_lead failed: %s", str(e))
        return 50


def generate_email_draft(lead_data: dict, tone: str = "professional") -> str:
    """Generate a personalized persuasion email using Gemini.

    Args:
        lead_data: Dict with name, company, deal_size, product fields.
        tone: Writing tone — professional, friendly, or urgent.

    Returns:
        Generated email string starting with 'Subject: ...'.
    """
    try:
        prompt = EMAIL_PROMPT.format(
            name=lead_data.get("name", "there"),
            company=lead_data.get("company", "your company"),
            product=lead_data.get("product", "our solution"),
            tone=tone,
            deal_size=lead_data.get("deal_size", 0),
        )
        response = model.generate_content(prompt)
        logger.info("Email draft generated for %s", lead_data.get("email"))
        return response.text
    except Exception as e:
        logger.error("Email generation failed: %s", str(e))
        name = lead_data.get("name", "there")
        return (
            f"Subject: Quick question for {name}\n\n"
            f"Dear {name},\n\nI'd love to connect about how we can help "
            f"{lead_data.get('company', 'your team')}.\n\nBest regards"
        )


def analyze_email(email_content: str) -> dict:
    """Analyze email persuasiveness and provide coaching feedback.

    Args:
        email_content: Full email text to analyze.

    Returns:
        Dict with persuasion_score, strengths, improvements, predicted_response_rate.
    """
    try:
        prompt = COACH_PROMPT.format(email_content=email_content)
        response = model.generate_content(prompt)
        cleaned = response.text.strip().strip("```json").strip("```").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON analysis response")
        return {
            "persuasion_score": 60,
            "strengths": ["Clear subject line"],
            "improvements": ["Add more personalization", "Strengthen CTA"],
            "predicted_response_rate": "15%",
        }
    except Exception as e:
        logger.error("Email analysis failed: %s", str(e))
        return {"persuasion_score": 50, "error": "Analysis unavailable"}


def get_followup_timing(urgency: str) -> int:
    """Get AI-recommended days until follow-up based on lead urgency.

    Args:
        urgency: Lead urgency level — low, medium, or high.

    Returns:
        Recommended number of days until follow-up (1-14).
    """
    try:
        prompt = FOLLOWUP_PROMPT.format(urgency=urgency)
        response = model.generate_content(prompt)
        days = max(1, min(14, int(response.text.strip())))
        return days
    except Exception as e:
        logger.error("Follow-up timing failed: %s", str(e))
        defaults = {"high": 1, "medium": 3, "low": 7}
        return defaults.get(urgency, 3)


def generate_followup_sequence(lead_data: dict, tone: str = "professional") -> list:
    """Generate a multi-step email follow-up sequence.

    Args:
        lead_data: Dict with name, company, product fields.
        tone: Writing tone for the sequence.

    Returns:
        List of dicts with day, subject, and body keys.
    """
    try:
        prompt = SEQUENCE_PROMPT.format(
            name=lead_data.get("name", "there"),
            company=lead_data.get("company", "your company"),
            product=lead_data.get("product", "our solution"),
            tone=tone,
        )
        response = model.generate_content(prompt)
        cleaned = response.text.strip().strip("```json").strip("```").strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error("Sequence generation failed: %s", str(e))
        return []


def handle_objection(objection: str) -> list:
    """Generate counter-responses to a sales objection.

    Args:
        objection: The objection raised by the prospect.

    Returns:
        List of dicts with response strings.
    """
    try:
        prompt = OBJECTION_PROMPT.format(objection=objection[:500])
        response = model.generate_content(prompt)
        cleaned = response.text.strip().strip("```json").strip("```").strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error("Objection handling failed: %s", str(e))
        return [
            {"response": "Thank you for sharing that concern. Let me address it..."}
        ]
