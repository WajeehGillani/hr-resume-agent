# src/tools/calendar.py
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from textwrap import dedent

from src.fallbacks import breaker, retry_policy

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

def _ensure_dt_utc(dt_or_iso: str | datetime) -> datetime:
    if isinstance(dt_or_iso, str):
        # Accept ISO like "2025-09-12T10:00:00" (assume local -> convert to UTC)
        # or "2025-09-12T10:00:00+05:00" (aware -> convert to UTC)
        try:
            dt = datetime.fromisoformat(dt_or_iso)
        except Exception:
            raise ValueError(f"Invalid datetime ISO: {dt_or_iso!r}")
    else:
        dt = dt_or_iso

    if dt.tzinfo is None:
        # Assume local time -> treat as UTC+0 for simplicity in this demo
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt

def _fmt_ics_dt(dt_utc: datetime) -> str:
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")

def _write_ics(
    summary: str,
    start_utc: datetime,
    duration_min: int = 30,
    location: str | None = None,
    filename: str = "invite.ics",
) -> str:
    end_utc = start_utc + timedelta(minutes=duration_min)
    uid = f"hr-{int(start_utc.timestamp())}@orchestrator"
    ics = dedent(f"""\
    BEGIN:VCALENDAR
    VERSION:2.0
    PRODID:-//HR Orchestrator//EN
    BEGIN:VEVENT
    UID:{uid}
    DTSTAMP:{_fmt_ics_dt(start_utc)}
    DTSTART:{_fmt_ics_dt(start_utc)}
    DTEND:{_fmt_ics_dt(end_utc)}
    SUMMARY:{summary}
    LOCATION:{location or ""}
    END:VEVENT
    END:VCALENDAR
    """).strip()

    out = ARTIFACTS / filename
    out.write_text(ics, encoding="utf-8")
    return str(out)

@retry_policy(attempts=3)
def _attempt_insert(insert_fn: Callable[[Dict[str, Any]], Any], payload: Dict[str, Any]) -> Any:
    """Retry wrapper around the real calendar insert call."""
    return insert_fn(payload)

def create_event_or_fallback(
    title: str,
    when_dt: str | datetime,
    *,
    duration_min: int = 30,
    location: Optional[str] = None,
    insert_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> Dict[str, Any]:
    """
    Try to insert calendar event using `insert_fn(payload)` if:
      - USE_REAL_CALENDAR == "1" AND
      - breaker.allow() is True AND
      - insert_fn is provided.
    Otherwise, or on failure, write an ICS fallback (artifacts/invite.ics).

    Returns dict with keys:
      - status: "inserted" | "fallback_ics" | "skipped_disabled" | "breaker_open"
      - ics_path: path to ICS (always present)
      - extra: optional info (e.g., error message)
    """
    start_utc = _ensure_dt_utc(when_dt)
    ics_path = _write_ics(title, start_utc, duration_min, location)  # always produce ICS (visible demo)

    use_real = os.getenv("USE_REAL_CALENDAR") == "1"
    if not use_real or insert_fn is None:
        return {"status": "skipped_disabled", "ics_path": ics_path}

    if not breaker.allow():
        return {"status": "breaker_open", "ics_path": ics_path}

    payload = {
        "summary": title,
        "start": start_utc.isoformat(),
        "end": (start_utc + timedelta(minutes=duration_min)).isoformat(),
        "location": location or "",
    }

    try:
        _attempt_insert(insert_fn, payload)
        breaker.record_success()
        return {"status": "inserted", "ics_path": ics_path}
    except Exception as e:
        breaker.record_failure()
        return {"status": "fallback_ics", "ics_path": ics_path, "extra": str(e)[:200]}
