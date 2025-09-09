from pydantic import BaseModel, Field
from typing import List, Optional

class Candidate(BaseModel):
    name: str = Field(..., min_length=1)
    email: Optional[str] = None
    years_exp: int = 0
    skills: List[str] = Field(default_factory=list)
    score: float = 0.0
    resume_path: str

class JD(BaseModel):
    title: str = Field(..., min_length=2)
    must_haves: List[str] = Field(..., min_items=1)
    nice_haves: List[str] = Field(default_factory=list)
    location: Optional[str] = None

class OrchestratorState(BaseModel):
    jd: JD
    candidates: List[Candidate] = Field(default_factory=list)
    shortlisted: List[Candidate] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    policy_violation: bool = False
    needs_disambiguation: bool = False
    tool_error: bool = False
    schema_ok: bool = False
    violations: List[str] = Field(default_factory=list)

def to_state(value):
    """Coerce a dict or model-like object to `OrchestratorState`.

    Supports Pydantic v1 and v2 by trying `model_validate` first, then `parse_obj`.
    """
    if isinstance(value, OrchestratorState):
        return value
    try:
        return OrchestratorState.model_validate(value)  # Pydantic v2
    except AttributeError:
        return OrchestratorState.parse_obj(value)  # Pydantic v1
