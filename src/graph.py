# src/graph.py
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from time import perf_counter

from src.state import OrchestratorState
from src.agents import screener, analyst, question_writer, reviewer
from src.tools.parser import load_text, parse_jd_to_struct, parse_resumes_from_dir
from src.tools.mcp_tool import parse_job_description_internal, validate_job_description_quality
from src.tools.email import draft_email
from src.tools.calendar import create_event_or_fallback
from src.guardrails.schemas import validate_final_output
from src.observability import get_tracer
from src.tools.google import create_calendar_event, create_gmail_draft
from src.tools.email import compose_email
from src.config import config
from src.display import display
from src.reports import generate_html_report, generate_summary_report
from src.templates import format_interview_email
from src.file_manager import get_artifacts_manager
from src.integrations import langsmith_integration

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
    ap = argparse.ArgumentParser(description="HR Interview Orchestrator - AI-Powered Candidate Screening")
    ap.add_argument("--jd", required=True, help="Path to JD (.txt/.md/.pdf/.docx)")
    ap.add_argument("--resumes", required=True, help="Directory with resumes")
    ap.add_argument("--when", default=None, help="ISO start time (e.g., 2025-09-12T10:00:00+05:00). If omitted, +1 day at 10:00 UTC.")
    ap.add_argument("--output-format", choices=["json", "html", "both"], default="both", help="Output format")
    ap.add_argument("--no-progress", action="store_true", help="Disable progress display")
    ap.add_argument("--quiet", action="store_true", help="Minimal output")
    ap.add_argument("--validate-jd", action="store_true", help="Validate job description quality using internal MCP tool")
    ap.add_argument("--parse-jd-only", action="store_true", help="Only parse job description and exit (MCP tool demo)")
    args = ap.parse_args()

    # Setup
    config.setup_directories()
    
    # Display header unless quiet
    if not args.quiet:
        display.show_header()
        display.show_config_status()
    
    # Initialize organized file management
    file_manager = None
    

    try:
        tracer = get_tracer()
        tracer.log_node("Main", "start")
        t0 = perf_counter()

        # Start progress tracking
        progress = None
        if not args.no_progress and not args.quiet:
            progress = display.start_progress(100)

        # Parse inputs with progress updates
        if progress:
            display.update_progress("📄 Loading job description...", 10)
        
        if not os.path.exists(args.jd):
            display.show_error(f"Job description file not found: {args.jd}")
            return 1
            
        if not os.path.isdir(args.resumes):
            display.show_error(f"Resumes directory not found: {args.resumes}")
            return 1

        jd_text = load_text(args.jd)
        
        if progress:
            display.update_progress("🔍 Parsing job requirements...", 20)
        
        jd_struct = parse_jd_to_struct(jd_text)
        
        # Handle parse-only mode
        if args.parse_jd_only:
            print("🔧 MCP Tool Demo: parse_job_description")
            print("=" * 45)
            try:
                # Use internal MCP tool
                mcp_result = parse_job_description_internal(jd_text, include_metadata=True)
                print(json.dumps(mcp_result, indent=2))
                
                # Also show quality validation
                quality_check = validate_job_description_quality(jd_text)
                print(f"\n📊 Quality Assessment:")
                print(f"   Score: {quality_check['quality_score']}/100 ({quality_check['quality_tier']})")
                if quality_check['suggestions']:
                    print(f"   Suggestions: {quality_check['suggestions']}")
                
                return 0
            except Exception as e:
                print(f"❌ MCP tool demo failed: {e}")
                return 1
        
        # Optional: Validate JD quality using internal MCP tool
        if args.validate_jd or not args.quiet:
            try:
                quality_check = validate_job_description_quality(jd_text)
                if args.validate_jd or quality_check['quality_score'] < 60:
                    if not args.quiet:
                        display.console.print(f"📊 [bold]JD Quality:[/bold] {quality_check['quality_score']}/100 ({quality_check['quality_tier']})")
                        if quality_check['suggestions']:
                            for suggestion in quality_check['suggestions'][:2]:  # Show top 2 suggestions
                                display.console.print(f"   💡 {suggestion}", style="yellow")
            except Exception:
                pass  # Silently skip if validation fails
        
        # Initialize file manager with job title for organized storage
        file_manager = get_artifacts_manager(job_title=jd_struct.title)
        
        
        if not args.quiet:
            display.show_job_summary(jd_struct)
        
        if progress:
            display.update_progress("📂 Processing candidate resumes...", 40)
        
        candidates = parse_resumes_from_dir(args.resumes)
        
        if not candidates:
            display.show_error("No valid candidate resumes found in the specified directory.")
            return 1

        # Build state and run graph with LangSmith tracing
        if progress:
            display.update_progress("🎯 Analyzing and scoring candidates...", 60)
        
        state = OrchestratorState(jd=jd_struct, candidates=candidates)
        
        # Wrap the graph execution with LangSmith tracing
        def run_graph():
            app = build_graph()
            raw = app.invoke(state.model_dump() if hasattr(state, "model_dump") else state)
            try:
                # Pydantic v2: model_validate parses nested structures too
                return OrchestratorState.model_validate(raw) if isinstance(raw, dict) else raw
            except Exception:
                # v1 fallback or any parsing edge-cases
                return OrchestratorState(**raw) if isinstance(raw, dict) else raw
        
        # Execute with LangSmith tracing if enabled
        if config.LANGSMITH_TRACING:
            state = langsmith_integration.tracer.trace_full_run(
                jd_title=jd_struct.title,
                candidates_count=len(candidates),
                processing_func=run_graph
            )
        else:
            state = run_graph()

    except FileNotFoundError as e:
        display.show_error("File not found", str(e))
        return 1
    except Exception as e:
        display.show_error("Processing failed", str(e))
        return 1


    # Validate final and write artifacts
    state.schema_ok, errs = validate_final_output(state)
    if not state.schema_ok:
        state.violations.extend(errs)

    # Email + Calendar (ICS fallback is always produced)
    emails: list[dict] = []
    drafts: list[dict] = []
    # Only schedule top N candidates by score (configurable)
    schedule_count = config.SCHEDULE_TOP_N
    top_candidates = sorted(state.shortlisted, key=lambda x: x.score, reverse=True)[:schedule_count] if state.shortlisted else []
    if top_candidates:
        for idx, c in enumerate(top_candidates, start=1):
            # Save redacted EML per candidate using organized paths
            has_email = bool(getattr(c, "email", None))
            eml_path = file_manager.get_email_path(c.name, idx)
            eml = draft_email(
                c.name,
                state.jd.title,
                "next week",
                to_email=getattr(c, "email", None),
                location=config.DEFAULT_LOCATION,
                filename=eml_path,
            )
            email_entry = {"name": c.name, "path": eml, "email": getattr(c, "email", None)}
            if not has_email:
                email_entry["info"] = "No email found in resume; To header omitted"
            emails.append(email_entry)
            # Optional: Gmail draft (if enabled and Google credentials are available)
            if config.USE_GMAIL_DRAFTS:
                try:
                    subj, body = compose_email(c.name, state.jd.title, "next week", location=config.DEFAULT_LOCATION)
                    if c.email:
                        d = create_gmail_draft(c.email, subj, body)
                        drafts.append({"name": c.name, "email": c.email, "draft_id": d.get("id") or (d.get("draft") or {}).get("id")})
                except Exception:
                    # Silently continue if Google credentials not available or Gmail fails
                    continue

    start_iso = args.when
    if not start_iso:
        # default: tomorrow 10:00 UTC
        start_iso = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()
    cal_multi: list[dict] = []
    for idx, c in enumerate(top_candidates, start=1):
        ics_path = file_manager.get_calendar_path(c.name, idx)
        ics_filename = Path(ics_path).name
        cal_res = create_event_or_fallback(
            f"Interview: {state.jd.title} - {c.name}",
            start_iso,
            duration_min=config.INTERVIEW_DURATION_MINUTES,
            location=config.DEFAULT_LOCATION,
            insert_fn=None,  # keep None for demo; ICS always written
            ics_filename=ics_filename
        )
        # Update the path to organized location
        cal_res["ics_path"] = ics_path
        # Optional: Google Calendar tentative event per candidate (only if enabled and configured)
        if config.USE_REAL_CALENDAR:
            try:
                start_dt = datetime.fromisoformat(start_iso)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                end_dt = start_dt + timedelta(minutes=config.INTERVIEW_DURATION_MINUTES)
                gcal = create_calendar_event(
                    f"Interview: {state.jd.title} - {c.name}",
                    start_dt.astimezone(timezone.utc).isoformat(),
                    end_dt.astimezone(timezone.utc).isoformat(),
                    location=config.DEFAULT_LOCATION,
                )
                cal_res["google_event_id"] = gcal.get("id")
                cal_res["google_html_link"] = gcal.get("htmlLink")
            except Exception:
                pass
        cal_multi.append({"name": c.name, **cal_res})

    # Optional: create Google Calendar event (tentative) if OAuth configured and enabled
    if config.USE_REAL_CALENDAR:
        try:
            start_dt = datetime.fromisoformat(start_iso)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            end_dt = start_dt + timedelta(minutes=30)
            gcal = create_calendar_event(
                f"Interview: {state.jd.title}",
                start_dt.astimezone(timezone.utc).isoformat(),
                end_dt.astimezone(timezone.utc).isoformat(),
                location="Google Meet",
            )
            cal_res["google_event_id"] = gcal.get("id")
            cal_res["google_html_link"] = gcal.get("htmlLink")
        except Exception:
            pass

    # --- Metrics summary ---
    elapsed_s = round(perf_counter() - t0, 3)
    metrics = {
        "elapsed_seconds": elapsed_s,
        "num_candidates": len(state.candidates),
        "shortlist_len": len(state.shortlisted),
        "needed_widening": bool(getattr(state, "needs_disambiguation", False)),
        "num_questions": len(state.questions),
        "calendar_status": cal_res.get("status"),
        "used_fallback": cal_res.get("status") != "inserted",
        "breaker_open": cal_res.get("status") == "breaker_open",
    }

    artifacts = {
        "emails": emails,
        "invites": cal_multi,
        "gmail_drafts": drafts,
    }

    # Generate comprehensive output
    if progress:
        display.update_progress("📊 Generating reports...", 90)

    # Enhanced JSON output
    enhanced_output = generate_summary_report(state, metrics, artifacts)
    
    # Save JSON report using organized paths
    json_path = None
    if args.output_format in ["json", "both"]:
        json_path = file_manager.get_report_path("json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(enhanced_output, f, indent=2)
    
    # Generate HTML report using organized paths
    html_path = None
    if args.output_format in ["html", "both"]:
        try:
            html_path = file_manager.get_report_path("html")
            generate_html_report(state, metrics, schedule_count, output_path=html_path)
        except Exception as e:
            if not args.quiet:
                display.show_warning(f"Could not generate HTML report: {e}")
    
        # Save run summary and create quick access
        if file_manager:
            summary_path = file_manager.save_run_summary(enhanced_output)
            file_manager.create_quick_access_links()
            file_manager.move_cache_files()
        
        # Log performance metrics to LangSmith
        if config.LANGSMITH_TRACING:
            langsmith_integration.tracer.log_performance_metrics(metrics)
            langsmith_integration.tracer.create_dataset_from_run(enhanced_output)
            

    if progress:
        display.finish_progress()

    # Display results unless quiet
    if not args.quiet:
        display.show_candidate_rankings(state.shortlisted, schedule_count)
        display.show_questions_preview(state.questions)
        display.show_artifacts_summary(artifacts, metrics)
        display.show_next_steps(artifacts)
        
        if html_path:
            display.console.print(f"\n📋 [bold green]HTML Report:[/bold green] {html_path}")
        if json_path:
            display.console.print(f"📊 [bold green]JSON Report:[/bold green] {json_path}")
        
        display.console.print(f"\n📁 [bold cyan]Run Directory:[/bold cyan] {file_manager.current_run_dir}")
        display.console.print(f"🔗 [bold cyan]Quick Access:[/bold cyan] {config.ARTIFACTS_DIR / 'latest'}")
        display.console.print(f"\n✅ [bold green]Processing complete![/bold green] All artifacts are organized by run.")

    tracer.log_node("Main", "done", **metrics)
    
    # Return 0 for success
    return 0


if __name__ == "__main__":
    main()
