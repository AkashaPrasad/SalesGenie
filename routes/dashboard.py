"""Dashboard routes — pipeline stats and main view."""

import logging

import google.auth.exceptions
from flask import Blueprint, jsonify, redirect, render_template, session, url_for
from googleapiclient.errors import HttpError

from app import cache
from config import Config
from services.auth_service import dict_to_credentials, refresh_credentials_if_expired
from services.drive_service import get_all_leads, get_sheets_service, initialize_sheet

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint("dashboard", __name__)


def _get_credentials():
    """Retrieve and refresh credentials from session.

    Returns:
        Credentials object or None if unauthenticated.
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


@dashboard_bp.route("/dashboard")
def dashboard():
    """Render the main sales pipeline dashboard.

    Returns:
        Rendered dashboard.html or redirect to login.
    """
    if not session.get("user_email"):
        return redirect(url_for("auth.login"))

    creds = _get_credentials()
    if creds:
        _ensure_sheet_initialized(creds)

    return render_template(
        "dashboard.html",
        user_name=session.get("user_name", "Sales Rep"),
        user_email=session.get("user_email", ""),
        stages=Config.PIPELINE_STAGES,
    )


@dashboard_bp.route("/api/dashboard/stats")
@cache.cached(timeout=60, key_prefix="pipeline_stats")
def get_pipeline_stats():
    """Return cached pipeline statistics from Google Sheets.

    Returns:
        JSON with deal counts, win rate, and average deal size.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    creds = _get_credentials()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    try:
        service = get_sheets_service(creds)
        leads = get_all_leads(service, Config.SPREADSHEET_ID)
        stats = _compute_pipeline_stats(leads)
        return jsonify(stats)
    except HttpError as e:
        logger.error("Failed to compute pipeline stats: %s", str(e))
        return jsonify({"error": "Failed to load stats"}), 503


@dashboard_bp.route("/api/dashboard/leads-by-stage")
def leads_by_stage():
    """Return leads grouped by pipeline stage for Kanban board.

    Returns:
        JSON dict mapping stage names to lead lists.
    """
    if not session.get("user_email"):
        return jsonify({"error": "Authentication required"}), 401

    creds = _get_credentials()
    if not creds:
        return jsonify({"error": "Authentication required"}), 401

    try:
        service = get_sheets_service(creds)
        leads = get_all_leads(service, Config.SPREADSHEET_ID)
        grouped = _group_leads_by_stage(leads)
        return jsonify({"stages": grouped})
    except HttpError as e:
        logger.error("Failed to group leads by stage: %s", str(e))
        return jsonify({"error": "Failed to load pipeline"}), 503


def _compute_pipeline_stats(leads: list) -> dict:
    """Compute summary statistics from a list of leads.

    Args:
        leads: List of lead dicts fetched from Sheets.

    Returns:
        Dict with total_leads, win_rate, avg_deal_size, and stage_counts.
    """
    if not leads:
        return {
            "total_leads": 0,
            "win_rate": 0,
            "avg_deal_size": 0,
            "stage_counts": {},
            "avg_score": 0,
        }

    stage_counts: dict = {}
    total_deal_size = 0
    won = 0
    closed = 0
    total_score = 0

    for lead in leads:
        stage = lead.get("stage", "Prospecting")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

        try:
            total_deal_size += int(lead.get("deal_size", 0))
        except (ValueError, TypeError):
            pass

        try:
            total_score += int(lead.get("score", 50))
        except (ValueError, TypeError):
            pass

        if stage == "Closed Won":
            won += 1
        if stage in ("Closed Won", "Closed Lost"):
            closed += 1

    win_rate = round((won / closed * 100) if closed else 0, 1)
    avg_deal = round(total_deal_size / len(leads)) if leads else 0
    avg_score = round(total_score / len(leads)) if leads else 0

    return {
        "total_leads": len(leads),
        "win_rate": win_rate,
        "avg_deal_size": avg_deal,
        "avg_score": avg_score,
        "stage_counts": stage_counts,
    }


def _group_leads_by_stage(leads: list) -> dict:
    """Group leads into a dict keyed by stage name.

    Args:
        leads: Flat list of lead dicts.

    Returns:
        Dict mapping stage name to list of leads in that stage.
    """
    grouped: dict = {stage: [] for stage in Config.PIPELINE_STAGES}
    for lead in leads:
        stage = lead.get("stage", "Prospecting")
        if stage not in grouped:
            grouped[stage] = []
        grouped[stage].append(lead)
    return grouped


def _ensure_sheet_initialized(creds) -> None:
    """Initialize Sheets headers if needed (best-effort, no crash).

    Args:
        creds: Google OAuth2 Credentials.
    """
    try:
        service = get_sheets_service(creds)
        initialize_sheet(service, Config.SPREADSHEET_ID)
    except HttpError as e:
        logger.warning("Sheet init skipped: %s", str(e))
