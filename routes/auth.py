"""OAuth2 authentication routes — login, callback, logout."""

import logging
import secrets

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

from services.auth_service import (
    credentials_to_dict,
    exchange_code_for_credentials,
    get_auth_url,
)

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    """Render landing page or redirect to dashboard if authenticated.

    Returns:
        Rendered index.html or redirect to dashboard.
    """
    if session.get("user_email"):
        return redirect(url_for("dashboard.dashboard"))
    return render_template("index.html")


@auth_bp.route("/login")
def login():
    """Initiate OAuth2 flow with a CSRF state token.

    Returns:
        Redirect to Google authorization URL.
    """
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    auth_url = get_auth_url(state)
    logger.info("OAuth2 login initiated")
    return redirect(auth_url)


@auth_bp.route("/oauth2callback")
def oauth2callback():
    """Handle Google OAuth2 callback and validate CSRF state.

    Returns:
        Redirect to dashboard on success, or error JSON on failure.
    """
    received_state = request.args.get("state")
    expected_state = session.pop("oauth_state", None)

    if not received_state or received_state != expected_state:
        logger.warning("OAuth state mismatch — possible CSRF attempt")
        return jsonify({"error": "Invalid state parameter"}), 403

    error = request.args.get("error")
    if error:
        logger.warning("OAuth2 error from Google: %s", error)
        return redirect(url_for("auth.index"))

    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400

    try:
        credentials = exchange_code_for_credentials(code)
        session["credentials"] = credentials_to_dict(credentials)
        _set_user_email_in_session(credentials)
        logger.info("OAuth2 login successful for user")
        return redirect(url_for("dashboard.dashboard"))
    except google.auth.exceptions.OAuthError as e:
        logger.error("OAuth token exchange failed: %s", str(e))
        return jsonify({"error": "Authentication failed"}), 401


@auth_bp.route("/logout")
def logout():
    """Clear session and redirect to landing page.

    Returns:
        Redirect to index.
    """
    session.clear()
    logger.info("User logged out")
    return redirect(url_for("auth.index"))


def _set_user_email_in_session(credentials) -> None:
    """Extract and store user email from credentials.

    Args:
        credentials: Google OAuth2 Credentials object.
    """
    try:
        import google.oauth2.id_token as id_token_module
        from google.auth.transport import requests as google_requests

        request_obj = google_requests.Request()
        id_info = id_token_module.verify_oauth2_token(credentials.id_token, request_obj)
        session["user_email"] = id_info.get("email", "unknown@gmail.com")
        session["user_name"] = id_info.get("name", "Sales Rep")
    except Exception as e:
        logger.warning("Could not extract email from id_token: %s", str(e))
        session["user_email"] = "authenticated@gmail.com"
        session["user_name"] = "Sales Rep"
