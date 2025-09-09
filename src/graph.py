# src/graph.py
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from datetime import datetime, timedelta, timezone

from langgraph.graph import StateGraph, END
from time import perf_counter

from src.state import OrchestratorState
from src.agents import screener, analyst, question_writer, reviewer
from src.tools.parser import load_text, parse_jd_to_struct, parse_resumes_from_dir
from src.tools.email import draft_email
from src.tools.calendar import create_event_or_fallback
from src.guardrails.schemas import validate_final_output
from src.observability import get_tracer

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

def build_graph():
    g = StateGraph(OrchestratorState)
    g.add_node("Screener", screener)
    g.add_node("Analyst", analyst)
    g.add_node("QuestionWriter", question_writer)
    g.add_node("Reviewer", reviewer)

    # Route to Reviewer when schema not ok (QuestionWriter sets schema_ok)
    def needs_review(state: OrchestratorState):
        return not state.schema_ok or state.policy_violation

    g.set_entry_point("Screener")
    g.add_edge("Screener", "Analyst")
    g.add_edge("Analyst", "QuestionWriter")
    g.add_conditional_edges("QuestionWriter", needs_review, {True: "Reviewer", False: END})
    g.add_edge("Reviewer", END)
    return g.compile()

def main():
    ap = argparse.ArgumentParser(description="HR Interview Orchestrator (LangGraph)")
    ap.add_argument("--jd", required=True, help="Path to JD (.txt/.md/.pdf/.docx)")
    ap.add_argument("--resumes", required=True, help="Directory with resumes")
    ap.add_argument("--when", default=None, help="ISO start time (e.g., 2025-09-12T10:00:00+05:00). If omitted, +1 day at 10:00 UTC.")
    args = ap.parse_args()

    tracer = get_tracer()
    tracer.log_node("Main", "start")
    t0 = perf_counter()

    # Parse inputs
    jd_text = load_text(args.jd)
    jd_struct = parse_jd_to_struct(jd_text)
    candidates = parse_resumes_from_dir(args.resumes)

    # Build state and run graph
    state = OrchestratorState(jd=jd_struct, candidates=candidates)
    app = build_graph()

    # LangGraph commonly returns a plain dict. Normalize back to Pydantic.
    raw = app.invoke(state.model_dump() if hasattr(state, "model_dump") else state)
    try:
        # Pydantic v2: model_validate parses nested structures too
        state = OrchestratorState.model_validate(raw) if isinstance(raw, dict) else raw
    except Exception:
        # v1 fallback or any parsing edge-cases
        state = OrchestratorState(**raw) if isinstance(raw, dict) else raw


    # Validate final and write artifacts
    state.schema_ok, errs = validate_final_output(state)
    if not state.schema_ok:
        state.violations.extend(errs)

    # Email + Calendar (ICS fallback is always produced)
    email_path = None
    if state.shortlisted:
        top = state.shortlisted[0]
        email_path = draft_email(top.name, state.jd.title, "next week", location="Google Meet")

    start_iso = args.when
    if not start_iso:
        # default: tomorrow 10:00 UTC
        start_iso = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()
    cal_res = create_event_or_fallback(
        f"Interview: {state.jd.title}",
        start_iso,
        duration_min=30,
        location="Google Meet",
        insert_fn=None  # keep None for demo; ICS always written
    )

    # --- Metrics summary ---
    elapsed_s = round(perf_counter() - t0, 3)
    metrics = {
        "elapsed_seconds": elapsed_s,
        "num_candidates": len(state.candidates),
        "shortlist_len": len(state.shortlisted),
        "needed_widening": bool(getattr(state, "needs_disambiguation", False) or getattr(state, "needs_disambiguination", False)),
        "num_questions": len(state.questions),
        "calendar_status": cal_res.get("status"),
        "used_fallback": cal_res.get("status") != "inserted",
        "breaker_open": cal_res.get("status") == "breaker_open",
    }

    out = {
        "jd_title": state.jd.title,
        "must_haves": state.jd.must_haves,
        "shortlist": [{"name": c.name, "score": c.score} for c in state.shortlisted],
        "questions": state.questions,
        "schema_ok": state.schema_ok,
        "violations": state.violations,
        "artifacts": {
            "email_eml": email_path,
            "invite_ics": cal_res.get("ics_path"),
        },
        "metrics": metrics,
    }

    (ARTIFACTS / "output.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    tracer.log_node("Main", "done", **metrics)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
