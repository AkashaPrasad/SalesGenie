"""Application configuration loaded exclusively from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central config class — all values from env vars, never hardcoded."""

    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    FLASK_SECRET_KEY: str = os.environ.get("FLASK_SECRET_KEY", "")
    REDIRECT_URI: str = os.environ.get(
        "REDIRECT_URI", "http://localhost:5000/oauth2callback"
    )
    SPREADSHEET_ID: str = os.environ.get("SPREADSHEET_ID", "")
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    PIPELINE_STAGES: list = [
        "Prospecting",
        "Contacted",
        "Proposal",
        "Closed Won",
        "Closed Lost",
    ]

    @classmethod
    def validate(cls) -> None:
        """Raise ValueError if any required config is missing."""
        required = [
            "GEMINI_API_KEY",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "FLASK_SECRET_KEY",
        ]
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
