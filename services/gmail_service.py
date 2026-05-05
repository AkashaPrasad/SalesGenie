"""Gmail API service for sending and reading emails."""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def get_gmail_service(credentials):
    """Build an authenticated Gmail API service object.

    Args:
        credentials: Google OAuth2 Credentials.

    Returns:
        Authenticated Gmail API service resource.
    """
    return build("gmail", "v1", credentials=credentials)


def send_email(service, to: str, subject: str, body: str) -> dict:
    """Send an email via Gmail API.

    Args:
        service: Authenticated Gmail service object.
        to: Recipient email address.
        subject: Email subject line.
        body: Plain text email body.

    Returns:
        Dict with 'id' of the sent message.

    Raises:
        HttpError: If the Gmail API call fails.
    """
    message = MIMEMultipart("alternative")
    message["to"] = to
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        result = (
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
        )
        logger.info("Email sent successfully: message_id=%s", result.get("id"))
        return result
    except HttpError as e:
        logger.error("Gmail API send failed to=%s: %s", to, str(e))
        raise


def list_recent_emails(service, max_results: int = 10) -> list:
    """Fetch the most recent sent emails.

    Args:
        service: Authenticated Gmail service object.
        max_results: Maximum number of messages to return.

    Returns:
        List of message resource dicts (id, threadId).
    """
    try:
        result = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["SENT"],
                maxResults=max_results,
            )
            .execute()
        )
        messages = result.get("messages", [])
        logger.info("Fetched %d recent sent emails", len(messages))
        return messages
    except HttpError as e:
        logger.error("Failed to list emails: %s", str(e))
        return []


def get_user_profile(service) -> dict:
    """Get the authenticated user's Gmail profile.

    Args:
        service: Authenticated Gmail service object.

    Returns:
        Dict with emailAddress and other profile fields.
    """
    try:
        return service.users().getProfile(userId="me").execute()
    except HttpError as e:
        logger.error("Failed to get Gmail profile: %s", str(e))
        return {}
