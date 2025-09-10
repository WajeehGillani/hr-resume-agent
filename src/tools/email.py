# src/tools/email.py
from __future__ import annotations
import os
from pathlib import Path
from textwrap import dedent
from typing import Optional
from datetime import datetime
from email.utils import formatdate

from src.guardrails.moderation import moderate_text
from src.guardrails.pii import redact

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

def compose_email(candidate_name: str, jd_title: str, when_human: str, *, location: Optional[str] = None, contact_name: str = "HR Team", contact_email: str = "hr@example.com") -> tuple[str, str]:
    subject = f"Interview for {jd_title}"
    location_line = f"\nLocation: {location}" if location else ""
    body = dedent(f"""\
        Hi {candidate_name},

        Thanks for applying for the {jd_title} role. We’d love to schedule a 30-minute interview on {when_human}.{location_line}

        Please reply with your availability and preferred time zone.

        Best,
        {contact_name}
        {contact_email}
    """)
    return subject, body

def draft_email(
    candidate_name: str,
    jd_title: str,
    when_human: str,
    *,
    to_email: Optional[str] = None,
    location: Optional[str] = None,
    contact_name: str = "HR Team",
    contact_email: str = "hr@example.com",
    filename: str = "email_candidate.eml"
) -> str:
    """
    Compose a polite interview invite and write artifacts/email_candidate.eml.
    - Runs moderation first; if flagged, replaces with a safe notice.
    - Always applies PII redaction to the saved artifact.
    Returns absolute path to the saved .eml file.
    """
    subject, body = compose_email(candidate_name, jd_title, when_human, location=location, contact_name=contact_name, contact_email=contact_email)

    # 1) Moderation
    is_safe, _ = moderate_text(body)
    if not is_safe:
        body = dedent(f"""\
            Subject: {subject}

            Hi {candidate_name},

            Your message triggered our content safety filters. A member of our team will follow up shortly.

            Best,
            {contact_name}
        """)

    # 2) Redact PII in artifact (preview-safe)
    body_redacted = redact(body)

    # 3) Save with minimal RFC 822 headers
    headers = []
    headers.append(f"From: {contact_email}")
    if to_email:
        headers.append(f"To: {to_email}")
    headers.append(f"Subject: {subject}")
    headers.append(f"Date: {formatdate(localtime=False)}")
    headers.append("MIME-Version: 1.0")
    headers.append("Content-Type: text/plain; charset=utf-8")
    headers.append("Content-Transfer-Encoding: 8bit")
    eml = "\n".join(headers) + "\n\n" + body_redacted

    # Handle both relative and absolute paths
    if os.path.isabs(filename):
        out_path = Path(filename)
    else:
        out_path = ARTIFACTS / filename
    
    # Ensure parent directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(eml, encoding="utf-8")

    return str(out_path)
