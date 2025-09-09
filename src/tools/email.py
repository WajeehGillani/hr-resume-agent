# src/tools/email.py
from __future__ import annotations
from pathlib import Path
from textwrap import dedent
from typing import Optional
from datetime import datetime

from src.guardrails.moderation import moderate_text
from src.guardrails.pii import redact

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

def draft_email(
    candidate_name: str,
    jd_title: str,
    when_human: str,
    *,
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
    subject = f"Interview for {jd_title}"
    location_line = f"\nLocation: {location}" if location else ""
    body = dedent(f"""\
        Subject: {subject}

        Hi {candidate_name},

        Thanks for applying for the {jd_title} role. We’d love to schedule a 30-minute interview on {when_human}.{location_line}

        Please reply with your availability and preferred time zone.

        Best,
        {contact_name}
        {contact_email}
    """)

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

    # 3) Save
    out_path = ARTIFACTS / filename
    out_path.write_text(body_redacted, encoding="utf-8")

    return str(out_path)
