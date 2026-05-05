"""Google Sheets API service — used as the lead CRM database."""

import logging
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

LEADS_RANGE = "Leads!A:J"
LEADS_HEADERS = [
    "Name",
    "Company",
    "Email",
    "Deal Size",
    "Stage",
    "Score",
    "Urgency",
    "Product",
    "Notes",
    "Created At",
]


def get_sheets_service(credentials):
    """Build an authenticated Google Sheets API service object.

    Args:
        credentials: Google OAuth2 Credentials.

    Returns:
        Authenticated Sheets API service resource.
    """
    return build("sheets", "v4", credentials=credentials)


def initialize_sheet(service, spreadsheet_id: str) -> None:
    """Write column headers to the sheet if it is empty.

    Args:
        service: Authenticated Sheets service object.
        spreadsheet_id: Target Google Sheet ID.
    """
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range="Leads!A1:J1",
            )
            .execute()
        )
        if not result.get("values"):
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="Leads!A1",
                valueInputOption="RAW",
                body={"values": [LEADS_HEADERS]},
            ).execute()
            logger.info("Sheet initialized with headers")
    except HttpError as e:
        logger.error("Sheet initialization failed: %s", str(e))


def add_lead_to_sheet(service, spreadsheet_id: str, lead: dict) -> dict:
    """Append a single lead row to the Google Sheet.

    Args:
        service: Authenticated Sheets service object.
        spreadsheet_id: Target Google Sheet ID.
        lead: Lead dict with name, company, email, deal_size, stage, score, etc.

    Returns:
        API response dict.

    Raises:
        HttpError: If the Sheets API call fails.
    """
    row = _lead_to_row(lead)
    try:
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=LEADS_RANGE,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            )
            .execute()
        )
        logger.info("Lead added to sheet: email=%s", lead.get("email"))
        return result
    except HttpError as e:
        logger.error("Sheets API append failed: %s", str(e))
        raise


def batch_add_leads(service, spreadsheet_id: str, leads: list) -> dict:
    """Add multiple leads in a single Sheets API call (efficient batching).

    Args:
        service: Authenticated Sheets service object.
        spreadsheet_id: Target Google Sheet ID.
        leads: List of lead dicts to append.

    Returns:
        API response dict.
    """
    if not leads:
        return {}
    rows = [_lead_to_row(lead) for lead in leads]
    try:
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=LEADS_RANGE,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": rows},
            )
            .execute()
        )
        logger.info("Batch added %d leads to sheet", len(leads))
        return result
    except HttpError as e:
        logger.error("Sheets batch append failed: %s", str(e))
        raise


def get_all_leads(service, spreadsheet_id: str) -> list:
    """Fetch all leads from the Google Sheet in a single API call.

    Args:
        service: Authenticated Sheets service object.
        spreadsheet_id: Target Google Sheet ID.

    Returns:
        List of lead dicts (headers as keys).
    """
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=LEADS_RANGE,
            )
            .execute()
        )
        rows = result.get("values", [])
        if len(rows) <= 1:
            return []
        header_keys = [h.lower().replace(" ", "_") for h in LEADS_HEADERS]
        return [
            dict(zip(header_keys, row + [""] * (len(header_keys) - len(row))))
            for row in rows[1:]
        ]
    except HttpError as e:
        logger.error("Failed to fetch leads from sheet: %s", str(e))
        return []


def update_lead_stage(
    service, spreadsheet_id: str, row_index: int, new_stage: str
) -> dict:
    """Update the pipeline stage for a specific lead row.

    Args:
        service: Authenticated Sheets service object.
        spreadsheet_id: Target Google Sheet ID.
        row_index: 0-based index of the lead in the data (excludes header).
        new_stage: New pipeline stage string.

    Returns:
        API response dict.
    """
    cell_range = f"Leads!E{row_index + 2}"
    try:
        result = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=cell_range,
                valueInputOption="RAW",
                body={"values": [[new_stage]]},
            )
            .execute()
        )
        logger.info("Lead stage updated: row=%d stage=%s", row_index, new_stage)
        return result
    except HttpError as e:
        logger.error("Failed to update lead stage: %s", str(e))
        raise


def log_sent_email(service, spreadsheet_id: str, email_log: dict) -> dict:
    """Log a sent email entry to a separate Emails sheet tab.

    Args:
        service: Authenticated Sheets service object.
        spreadsheet_id: Target Google Sheet ID.
        email_log: Dict with to, subject, sent_at fields.

    Returns:
        API response dict.
    """
    row = [
        email_log.get("to", ""),
        email_log.get("subject", ""),
        email_log.get("sent_at", datetime.now().isoformat()),
        email_log.get("message_id", ""),
    ]
    try:
        return (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range="Emails!A:D",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            )
            .execute()
        )
    except HttpError as e:
        logger.error("Failed to log sent email: %s", str(e))
        return {}


def _lead_to_row(lead: dict) -> list:
    """Convert a lead dict to a Sheets row list.

    Args:
        lead: Lead dictionary.

    Returns:
        Ordered list matching LEADS_HEADERS columns.
    """
    return [
        lead.get("name", ""),
        lead.get("company", ""),
        lead.get("email", ""),
        lead.get("deal_size", 0),
        lead.get("stage", "Prospecting"),
        lead.get("score", 50),
        lead.get("urgency", "medium"),
        lead.get("product", ""),
        lead.get("notes", ""),
        lead.get("created_at", datetime.now().isoformat()),
    ]
