"""Google Calendar API service for scheduling follow-up events."""

import logging
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "Asia/Kolkata"


def get_calendar_service(credentials):
    """Build an authenticated Google Calendar API service object.

    Args:
        credentials: Google OAuth2 Credentials.

    Returns:
        Authenticated Calendar API service resource.
    """
    return build("calendar", "v3", credentials=credentials)


def schedule_followup(
    service,
    lead_name: str,
    lead_email: str,
    followup_date: datetime,
    notes: str = "",
) -> dict:
    """Create a follow-up reminder event in Google Calendar.

    Args:
        service: Authenticated Calendar service object.
        lead_name: Contact name used in the event title.
        lead_email: Lead's email added as an attendee.
        followup_date: Datetime for the follow-up appointment.
        notes: Optional AI-generated talking points for the event description.

    Returns:
        Created event dict containing 'id' and 'htmlLink'.

    Raises:
        HttpError: If the Calendar API call fails.
    """
    end_date = followup_date + timedelta(minutes=30)
    event = _build_event(lead_name, lead_email, followup_date, end_date, notes)

    try:
        result = (
            service.events()
            .insert(
                calendarId="primary",
                body=event,
                sendUpdates="none",
            )
            .execute()
        )
        logger.info("Calendar event created: event_id=%s", result.get("id"))
        return result
    except HttpError as e:
        logger.error("Calendar API error creating event: %s", str(e))
        raise


def _build_event(
    lead_name: str,
    lead_email: str,
    start: datetime,
    end: datetime,
    notes: str,
) -> dict:
    """Build the Calendar event payload.

    Args:
        lead_name: Name for the event title.
        lead_email: Attendee email.
        start: Event start datetime.
        end: Event end datetime.
        notes: Description text for the event.

    Returns:
        Event resource dict ready for the Calendar API.
    """
    return {
        "summary": f"Follow up with {lead_name} — SalesGenie",
        "description": notes
        or f"AI-scheduled follow-up with {lead_name}. Review deal status and next steps.",
        "start": {"dateTime": start.isoformat(), "timeZone": DEFAULT_TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": DEFAULT_TIMEZONE},
        "attendees": [{"email": lead_email}],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 60},
            ],
        },
    }


def list_upcoming_followups(service, max_results: int = 10) -> list:
    """List upcoming SalesGenie follow-up events.

    Args:
        service: Authenticated Calendar service object.
        max_results: Maximum events to return.

    Returns:
        List of event resource dicts.
    """
    try:
        now = datetime.utcnow().isoformat() + "Z"
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
                q="SalesGenie",
            )
            .execute()
        )
        events = result.get("items", [])
        logger.info("Fetched %d upcoming follow-up events", len(events))
        return events
    except HttpError as e:
        logger.error("Failed to list calendar events: %s", str(e))
        return []
