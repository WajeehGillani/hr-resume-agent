from __future__ import annotations
import os
import base64
from typing import Optional, Tuple
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

# Scopes: calendar events and Gmail compose
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.compose",
]

TOKENS_DIR = Path.cwd() / ".tokens"
TOKENS_DIR.mkdir(parents=True, exist_ok=True)


def _creds() -> Optional[Credentials]:
    """
    Returns OAuth credentials using these sources (in order):
    - Token file from env `GOOGLE_TOKEN_FILE`
    - Token file `./token.json`
    - Token file `./.tokens/google_token.json`

    If the token is missing/invalid or lacks required scopes, and a client
    secret is available, runs local consent and saves the refreshed token to
    the chosen token path.

    Client secret is located via:
    - Env `GOOGLE_CLIENT_SECRET_FILE` or `GOOGLE_CREDENTIALS_FILE`
    - Fallback `./credentials.json`
    """
    # Resolve paths
    token_path_env = os.getenv("GOOGLE_TOKEN_FILE")
    token_candidates = [
        Path(token_path_env) if token_path_env else None,
        Path.cwd() / "token.json",
        TOKENS_DIR / "google_token.json",
    ]
    token_path = next((p for p in token_candidates if p is not None), TOKENS_DIR / "google_token.json")

    secret_env = os.getenv("GOOGLE_CLIENT_SECRET_FILE") or os.getenv("GOOGLE_CREDENTIALS_FILE")
    secret_candidates = [
        Path(secret_env) if secret_env else None,
        Path.cwd() / "credentials.json",
    ]
    secret_path = next((p for p in secret_candidates if p is not None and p.exists()), None)

    creds: Optional[Credentials] = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None

    def _run_flow() -> Optional[Credentials]:
        if not secret_path or not secret_path.exists():
            return None
        flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
        c = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(c.to_json(), encoding="utf-8")
        return c

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = _run_flow()
        else:
            creds = _run_flow()

    # Ensure required scopes
    try:
        has_scopes = getattr(creds, "has_scopes", None)
        if callable(has_scopes) and not creds.has_scopes(SCOPES):
            new_creds = _run_flow()
            if new_creds is not None:
                creds = new_creds
    except Exception:
        pass

    return creds


def create_calendar_event(summary: str, start_iso_utc: str, end_iso_utc: str, location: Optional[str] = None) -> dict:
    """Create a Calendar event (defaults to status tentative). Returns API response.

    Requires env `GOOGLE_CLIENT_SECRET_FILE` pointing to OAuth client secret JSON.
    """
    creds = _creds()
    if creds is None:
        raise RuntimeError("Google credentials not configured. Set GOOGLE_CLIENT_SECRET_FILE.")
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    body = {
        "summary": summary,
        "location": location or "",
        "start": {"dateTime": start_iso_utc, "timeZone": "UTC"},
        "end": {"dateTime": end_iso_utc, "timeZone": "UTC"},
        "status": "tentative",
    }
    return service.events().insert(calendarId="primary", body=body).execute()


def create_gmail_draft(to_email: str, subject: str, body_text: str) -> dict:
    """Create a Gmail draft. Returns API response.

    Requires env `GOOGLE_CLIENT_SECRET_FILE` pointing to OAuth client secret JSON.
    """
    creds = _creds()
    if creds is None:
        raise RuntimeError("Google credentials not configured. Set GOOGLE_CLIENT_SECRET_FILE.")
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    raw = f"From: me\nTo: {to_email}\nSubject: {subject}\n\n{body_text}".encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("utf-8")
    draft = {"message": {"raw": encoded}}
    return service.users().drafts().create(userId="me", body={"message": draft["message"]}).execute()


