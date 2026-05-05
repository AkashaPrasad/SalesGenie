"""Outreach routes — AI email generation, sending, and follow-up scheduling."""

import logging
from datetime import datetime, timedelta

import google.auth.exceptions
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from googleapiclient.errors import HttpError

from app import limiter
from config import Config
from services.auth_service import dict_to_credentials, refresh_credentials_if_expired
from services.calendar_service import get_calendar_service, schedule_followup
from services.drive_service import get_sheets_service, log_sent_email
from services.gemini_service import (
    analyze_email,
    generate_email_draft,
    generate_followup_sequence,
    get_followup_timing,
    handle_objection,
)
from services.gmail_service import get_gmail_service, send_email

logger = logging.getLogger(__name__)
outreach_bp = Blueprint("outreach", __name__)


def _get_credentials():
    """Retrieve and refresh credentials from session.

    Returns:
        Credentials object or None.
    """
    cred_dict = session.get("credentials")
    if not cred_dict:
        return None
    try:
        creds = dict_to_credentials(cred_dict)
        return refresh_credentials_if_expired(creds)
    except google.auth.exceptions.RefreshError as e:
        logger.error("Credential refresh failed: %s", str(e))
        return None


@outreach_bp.route("/outreach")
def outreach_page():
    """Render the email composer page.

    Returns:
        Rendered outreach.html or redirect to login.
    """
    if not session.get("user_email"):
        return redirect(url_for("auth.login"))
    return render_template(
        "outreach.html",
        user_name=session.get("user_name", "Sales Rep"),
    )


@outreach_bp.route("/api/outreach/generate", methods=["POST"])
@limiter.limit("10 per minute")
def generate_email():
    """Generate a personalized sales email via Gemini AI.

    Returns:
        JSON with email_draft and persuasion analysis.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    lead_name = data.get("lead_name", "").strip()
    if not lead_name or len(lead_name) < 2:
        return jsonify({"error": "lead_name must be at least 2 characters"}), 400

    lead_data = _extract_lead_data(data)
    tone = data.get("tone", "professional")

    draft = generate_email_draft(lead_data, tone=tone)
    analysis = analyze_email(draft)

    logger.info("Email draft generated for lead: %s", lead_name)
    return jsonify({"email_draft": draft, "analysis": analysis})


@outreach_bp.route("/api/outreach/send", methods=["POST"])
@limiter.limit("20 per hour")
def send_outreach_email():
    """Send a finalized email via Gmail API and log it to Sheets.

    Returns:
        JSON with message_id on success.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    to = data.get("to", "").strip()
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()

    if not to or "@" not in to:
        return jsonify({"error": "Valid recipient email required"}), 400
    if not subject:
        return jsonify({"error": "Subject is required"}), 400
    if not body:
        return jsonify({"error": "Email body is required"}), 400

    creds = _get_credentials()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    try:
        gmail = get_gmail_service(creds)
        result = send_email(gmail, to, subject, body)
        _log_email_to_sheet(creds, to, subject, result.get("id", ""))
        return jsonify(
            {"message": "Email sent successfully", "message_id": result.get("id")}
        )
    except HttpError as e:
        logger.error("Gmail send failed: %s", str(e))
        return jsonify({"error": "Failed to send email"}), 503


@outreach_bp.route("/api/outreach/schedule-followup", methods=["POST"])
def schedule_follow_up():
    """Schedule a follow-up reminder in Google Calendar.

    Returns:
        JSON with event link on success.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    lead_name = data.get("lead_name", "").strip()
    lead_email = data.get("lead_email", "").strip()
    urgency = data.get("urgency", "medium")

    if not lead_name or not lead_email:
        return jsonify({"error": "lead_name and lead_email are required"}), 400

    creds = _get_credentials()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    days = get_followup_timing(urgency)
    followup_dt = datetime.now() + timedelta(days=days)
    notes = data.get("notes", "")

    try:
        cal = get_calendar_service(creds)
        event = schedule_followup(cal, lead_name, lead_email, followup_dt, notes)
        return jsonify(
            {
                "message": f"Follow-up scheduled in {days} days",
                "event_link": event.get("htmlLink"),
                "followup_date": followup_dt.isoformat(),
            }
        )
    except HttpError as e:
        logger.error("Calendar scheduling failed: %s", str(e))
        return jsonify({"error": "Failed to schedule follow-up"}), 503


@outreach_bp.route("/api/outreach/sequence", methods=["POST"])
@limiter.limit("5 per minute")
def generate_sequence():
    """Generate a multi-step follow-up email sequence.

    Returns:
        JSON with list of sequence emails.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    lead_data = _extract_lead_data(data)
    tone = data.get("tone", "professional")
    sequence = generate_followup_sequence(lead_data, tone=tone)
    return jsonify({"sequence": sequence})


@outreach_bp.route("/api/outreach/objection", methods=["POST"])
@limiter.limit("10 per minute")
def handle_sales_objection():
    """Generate counter-responses to a prospect objection.

    Returns:
        JSON list of counter-response suggestions.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True)
    objection = (data or {}).get("objection", "").strip()
    if not objection:
        return jsonify({"error": "objection field required"}), 400

    responses = handle_objection(objection)
    return jsonify({"responses": responses})


def _extract_lead_data(data: dict) -> dict:
    """Extract lead fields from request data.

    Args:
        data: Raw request JSON dict.

    Returns:
        Normalized lead data dict.
    """
    return {
        "name": data.get("lead_name", data.get("name", "there")),
        "company": data.get("company", "your company"),
        "email": data.get("lead_email", data.get("email", "")),
        "deal_size": data.get("deal_size", 0),
        "product": data.get("product", "our solution"),
        "urgency": data.get("urgency", "medium"),
    }


def _log_email_to_sheet(creds, to: str, subject: str, message_id: str) -> None:
    """Log a sent email to Google Sheets asynchronously (best-effort).

    Args:
        creds: Google OAuth2 Credentials.
        to: Recipient email.
        subject: Email subject.
        message_id: Gmail message ID.
    """
    try:
        sheets = get_sheets_service(creds)
        log_sent_email(
            sheets,
            Config.SPREADSHEET_ID,
            {"to": to, "subject": subject, "message_id": message_id},
        )
    except HttpError as e:
        logger.warning("Email logging to sheet failed (non-critical): %s", str(e))
