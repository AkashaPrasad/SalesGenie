"""Google OAuth2 authentication service."""

import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _build_client_config() -> dict:
    """Build OAuth2 client config dict from environment variables."""
    return {
        "web": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.environ.get("REDIRECT_URI")],
        }
    }


def get_flow() -> Flow:
    """Create a new OAuth2 Flow from environment credentials.

    Returns:
        Configured google_auth_oauthlib Flow instance.
    """
    return Flow.from_client_config(
        _build_client_config(),
        scopes=SCOPES,
        redirect_uri=os.environ.get("REDIRECT_URI"),
    )


def get_auth_url(state: str) -> str:
    """Generate the Google OAuth2 authorization URL.

    Args:
        state: CSRF state token to embed in the auth URL.

    Returns:
        Full authorization URL string to redirect the user to.
    """
    flow = get_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    logger.info("OAuth2 authorization URL generated")
    return auth_url


def exchange_code_for_credentials(code: str) -> Credentials:
    """Exchange an authorization code for OAuth2 credentials.

    Args:
        code: Authorization code received from Google callback.

    Returns:
        Google OAuth2 Credentials object.
    """
    flow = get_flow()
    flow.fetch_token(code=code)
    logger.info("OAuth2 token exchange completed successfully")
    return flow.credentials


def credentials_to_dict(credentials: Credentials) -> dict:
    """Serialize credentials for server-side session storage.

    Args:
        credentials: Google OAuth2 Credentials object.

    Returns:
        Dict safe for session storage (no raw client_secret exposure).
    """
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
    }


def dict_to_credentials(cred_dict: dict) -> Credentials:
    """Deserialize credentials from session storage.

    Args:
        cred_dict: Dict previously created by credentials_to_dict.

    Returns:
        Reconstructed Google OAuth2 Credentials object.
    """
    return Credentials(
        token=cred_dict["token"],
        refresh_token=cred_dict.get("refresh_token"),
        token_uri=cred_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        scopes=cred_dict.get("scopes", SCOPES),
    )


def refresh_credentials_if_expired(credentials: Credentials) -> Credentials:
    """Refresh token if expired.

    Args:
        credentials: Existing credentials that may be expired.

    Returns:
        Refreshed credentials.
    """
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        logger.info("OAuth2 credentials refreshed successfully")
    return credentials
