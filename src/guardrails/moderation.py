# src/guardrails/moderation.py
from __future__ import annotations
from typing import Tuple, Any
from openai import OpenAI

def moderate_text(text: str) -> Tuple[bool, Any]:
    """
    Returns (is_safe, raw_response). Uses OpenAI 'omni-moderation-latest'.
    Fail-safe: if API errors, we treat as safe to avoid blocking demo runs.
    """
    try:
        client = OpenAI()
        resp = client.moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
        flagged = any(r.flagged for r in resp.results)
        return (not flagged, resp)
    except Exception as e:
        # Fail-open: don't block the flow during local dev
        return (True, {"error": str(e)})
