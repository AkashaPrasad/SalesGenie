"""Lead management routes — CRUD operations with AI scoring."""

import logging

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

from config import Config
from models.lead import Lead, validate_lead_input
from services.auth_service import dict_to_credentials, refresh_credentials_if_expired
from services.drive_service import (
    add_lead_to_sheet,
    get_all_leads,
    get_sheets_service,
    update_lead_stage,
)
from services.gemini_service import score_lead
from services.lead_scorer import validate_lead_for_scoring

logger = logging.getLogger(__name__)
leads_bp = Blueprint("leads", __name__)


def _require_auth():
    """Check session for valid credentials.

    Returns:
        Credentials object or None if unauthenticated.
    """
    cred_dict = session.get("credentials")
    if not cred_dict:
        return None
    try:
        creds = dict_to_credentials(cred_dict)
        creds = refresh_credentials_if_expired(creds)
        session["credentials"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "scopes": list(creds.scopes) if creds.scopes else [],
        }
        return creds
    except google.auth.exceptions.RefreshError as e:
        logger.error("Credential refresh failed: %s", str(e))
        return None


@leads_bp.route("/leads")
def leads_page():
    """Render the lead management page.

    Returns:
        Rendered leads.html template or redirect to login.
    """
    if not session.get("user_email"):
        return redirect(url_for("auth.login"))
    return render_template(
        "leads.html",
        stages=Config.PIPELINE_STAGES,
        user_name=session.get("user_name", "Sales Rep"),
    )


@leads_bp.route("/api/leads", methods=["GET"])
def get_leads():
    """Fetch all leads from Google Sheets.

    Returns:
        JSON list of leads or error response.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    creds = _require_auth()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    try:
        service = get_sheets_service(creds)
        leads = get_all_leads(service, Config.SPREADSHEET_ID)
        return jsonify({"leads": leads, "count": len(leads)})
    except HttpError as e:
        logger.error("Failed to fetch leads: %s", str(e))
        return jsonify({"error": "Failed to fetch leads from database"}), 503


@leads_bp.route("/api/leads", methods=["POST"])
def create_lead():
    """Create a new lead, score it with Gemini, and save to Sheets.

    Returns:
        JSON with created lead data and 201 status, or error.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    is_valid, error_msg = validate_lead_input(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    creds = _require_auth()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    lead = Lead.from_dict(data)
    lead = _apply_ai_score(lead)

    try:
        service = get_sheets_service(creds)
        add_lead_to_sheet(service, Config.SPREADSHEET_ID, lead.to_dict())
        logger.info("Lead created: email=%s score=%d", lead.email, lead.score)
        return jsonify({"lead": lead.to_dict(), "message": "Lead created"}), 201
    except HttpError as e:
        logger.error("Failed to save lead to sheet: %s", str(e))
        return jsonify({"error": "Failed to save lead"}), 503


@leads_bp.route("/api/leads/<int:row_index>/stage", methods=["PATCH"])
def update_stage(row_index: int):
    """Update a lead's pipeline stage.

    Args:
        row_index: 0-based index of the lead row.

    Returns:
        JSON success message or error.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json(silent=True)
    if not data or not data.get("stage"):
        return jsonify({"error": "Stage field required"}), 400

    creds = _require_auth()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    try:
        service = get_sheets_service(creds)
        update_lead_stage(service, Config.SPREADSHEET_ID, row_index, data["stage"])
        return jsonify({"message": "Stage updated successfully"})
    except HttpError as e:
        logger.error("Stage update failed: %s", str(e))
        return jsonify({"error": "Failed to update stage"}), 503


@leads_bp.route("/api/leads/search")
def search_leads():
    """Search leads by name, company, or email.

    Returns:
        JSON list of matching leads.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    query = request.args.get("q", "").strip().lower()
    creds = _require_auth()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    try:
        service = get_sheets_service(creds)
        all_leads = get_all_leads(service, Config.SPREADSHEET_ID)
        if not query:
            return jsonify({"leads": all_leads})
        filtered = [
            lead
            for lead in all_leads
            if query in lead.get("name", "").lower()
            or query in lead.get("company", "").lower()
            or query in lead.get("email", "").lower()
        ]
        return jsonify({"leads": filtered})
    except HttpError as e:
        logger.error("Lead search failed: %s", str(e))
        return jsonify({"error": "Search failed"}), 503


def _apply_ai_score(lead: Lead) -> Lead:
    """Score the lead with Gemini and update the score field.

    Args:
        lead: Lead instance to score.

    Returns:
        Lead with updated score field.
    """
    if validate_lead_for_scoring(lead.to_dict()):
        lead.score = score_lead(lead.to_dict())
    return lead
