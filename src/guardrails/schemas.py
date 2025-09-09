# src/guardrails/schemas.py
from __future__ import annotations
from typing import List, Tuple
from pydantic import BaseModel, Field, ValidationError

from src.state import OrchestratorState

# Final artifact schema (what we plan to save in output.json)
class FinalOutput(BaseModel):
    jd_title: str = Field(..., min_length=2)
    must_haves: List[str] = Field(default_factory=list)
    top_candidates: List[str] = Field(..., min_items=1)  # names only for artifact simplicity
    questions: List[str] = Field(..., min_items=5, max_items=20)

def validate_state_transition(state: OrchestratorState) -> Tuple[bool, List[str]]:
    """
    Light checks after nodes to route to Reviewer when needed.
    """
    violations: List[str] = []

    # Candidates: names must be non-empty strings
    for c in state.shortlisted:
        if not isinstance(c.name, str) or not c.name.strip():
            violations.append("Shortlisted candidate missing valid name")

    # Questions: ensure 5..20 for mid-pipeline (we'll target 8..12 later)
    if not isinstance(state.questions, list):
        violations.append("Questions not a list")
    else:
        q_clean = [q for q in state.questions if isinstance(q, str) and q.strip()]
        if len(q_clean) < 5:
            violations.append("Too few questions (<5)")
        if len(q_clean) > 20:
            violations.append("Too many questions (>20)")

    return (len(violations) == 0, violations)

def validate_final_output(state: OrchestratorState) -> Tuple[bool, List[str]]:
    """
    Strict validation for the artifact we write at the end.
    """
    data = {
        "jd_title": state.jd.title,
        "must_haves": list(state.jd.must_haves),
        "top_candidates": [c.name for c in state.shortlisted],
        "questions": list(state.questions),
    }
    try:
        FinalOutput(**data)
        return True, []
    except ValidationError as e:
        return False, [str(e)]
