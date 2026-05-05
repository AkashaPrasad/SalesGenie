"""Lead data model using Python dataclasses."""

from dataclasses import dataclass, field
from datetime import datetime


VALID_STAGES = [
    "Prospecting",
    "Contacted",
    "Proposal",
    "Closed Won",
    "Closed Lost",
]

VALID_URGENCY = ["low", "medium", "high"]


@dataclass
class Lead:
    """Represents a sales lead in the CRM pipeline.

    Attributes:
        name: Full name of the lead contact.
        company: Company name.
        email: Business email address.
        deal_size: Estimated deal value in USD.
        stage: Current pipeline stage.
        urgency: Lead urgency level (low/medium/high).
        score: AI-generated quality score (1-100).
        notes: Additional context or notes.
        created_at: ISO timestamp of creation.
        product: Product being pitched to this lead.
    """

    name: str
    company: str
    email: str
    deal_size: int = 0
    stage: str = "Prospecting"
    urgency: str = "medium"
    score: int = 50
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    product: str = ""

    def to_dict(self) -> dict:
        """Convert lead to a plain dictionary.

        Returns:
            Dict representation of the lead.
        """
        return {
            "name": self.name,
            "company": self.company,
            "email": self.email,
            "deal_size": self.deal_size,
            "stage": self.stage,
            "urgency": self.urgency,
            "score": self.score,
            "notes": self.notes,
            "created_at": self.created_at,
            "product": self.product,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Lead":
        """Create a Lead from a dictionary (e.g., from Sheets row).

        Args:
            data: Dictionary with lead field values.

        Returns:
            Lead dataclass instance.
        """

        def _safe_int(val: object, default: int) -> int:
            try:
                return int(val) if str(val).strip() else default
            except (ValueError, TypeError):
                return default

        return cls(
            name=data.get("name", ""),
            company=data.get("company", ""),
            email=data.get("email", ""),
            deal_size=_safe_int(data.get("deal_size", 0), 0),
            stage=data.get("stage", "Prospecting"),
            urgency=data.get("urgency", "medium"),
            score=_safe_int(data.get("score", 50), 50),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            product=data.get("product", ""),
        )

    @classmethod
    def from_sheet_row(cls, headers: list, row: list) -> "Lead":
        """Create a Lead from a Google Sheets row.

        Args:
            headers: Column header names.
            row: Row values from the sheet.

        Returns:
            Lead dataclass instance.
        """
        row_padded = row + [""] * (len(headers) - len(row))
        data = dict(zip([h.lower().replace(" ", "_") for h in headers], row_padded))
        return cls.from_dict(data)


def validate_lead_input(data: dict) -> tuple:
    """Validate raw input data before creating a Lead.

    Args:
        data: Raw dict from request JSON.

    Returns:
        Tuple of (is_valid: bool, error_message: str).
    """
    name = data.get("name", "").strip()
    if not name or len(name) < 2:
        return False, "Name must be at least 2 characters"

    email = data.get("email", "").strip()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return False, "Valid email address required"

    company = data.get("company", "").strip()
    if not company or len(company) < 2:
        return False, "Company name must be at least 2 characters"

    deal_size = data.get("deal_size", 0)
    try:
        int(deal_size)
    except (ValueError, TypeError):
        return False, "Deal size must be a whole number"

    stage = data.get("stage", "Prospecting")
    if stage not in VALID_STAGES:
        return False, f"Stage must be one of: {', '.join(VALID_STAGES)}"

    urgency = data.get("urgency", "medium")
    if urgency not in VALID_URGENCY:
        return False, f"Urgency must be one of: {', '.join(VALID_URGENCY)}"

    return True, ""
