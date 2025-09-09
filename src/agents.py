# src/agents.py
from __future__ import annotations
from typing import List, Iterable, Tuple
import re
from openai import OpenAI  # used by QuestionWriter (already implemented earlier)

from src.state import OrchestratorState, JD, Candidate
from src.guardrails.schemas import validate_state_transition, validate_final_output
from src.tools.retriever import LocalQuestionBank, build_query_from_jd
from src.observability import get_tracer

TRACER = get_tracer()

# ---------- Helpers ----------
def _canonize(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    for s in items:
        s = s.strip().lower()
        s = re.sub(r"[\s/|,;]+", " ", s)
        s = re.sub(r"[^a-z0-9 +#.\-]", "", s)
        if s:
            out.append(s)
    return out

def _overlap(required: Iterable[str], skills: Iterable[str]) -> float:
    R = set(_canonize(required))
    S = set(_canonize(skills))
    if not R:
        return 0.0
    return len(R & S) / max(1, len(R))

def _score_candidate(jd: JD, c: Candidate) -> float:
    must = _overlap(jd.must_haves, c.skills)
    nice = _overlap(jd.nice_haves, c.skills) if jd.nice_haves else 0.0
    exp_bonus = min(max(c.years_exp, 0) / 10.0, 0.3)
    return round(0.7 * must + 0.3 * nice + exp_bonus, 4)

def _shortlist(jd: JD, candidates: List[Candidate], top_n: int, min_score: float) -> List[Candidate]:
    scored: List[Tuple[float, Candidate]] = []
    for c in candidates:
        s = _score_candidate(jd, c)
        c.score = s
        scored.append((s, c))
    scored.sort(key=lambda t: t[0], reverse=True)
    filtered = [c for s, c in scored if s >= min_score]
    if not filtered:
        filtered = [c for _, c in scored[:top_n]]
    return filtered[:top_n]

# ---------- Nodes ----------
def screener(state: OrchestratorState) -> OrchestratorState:
    TRACER.log_node("Screener", "start")
    # Dedup/clean must_haves; require at least 3
    mh = [m.strip() for m in state.jd.must_haves if isinstance(m, str) and m.strip()]
    seen = set()
    cleaned = []
    for m in mh:
        k = m.lower()
        if k not in seen:
            seen.add(k); cleaned.append(m)
    state.jd.must_haves = cleaned
    if len(state.jd.must_haves) < 3:
        state.needs_disambiguation = True
    TRACER.log_node("Screener", "done", must_haves=len(state.jd.must_haves), needs_disambiguation=state.needs_disambiguation)
    return state

def analyst(
    state: OrchestratorState,
    *,
    top_n_first: int = 5,
    min_score_first: float = 0.35,
    top_n_wide: int = 7,
    widen_factor: float = 0.8
) -> OrchestratorState:
    TRACER.log_node("Analyst", "start", candidates=len(state.candidates))
    shortlist = _shortlist(state.jd, state.candidates, top_n_first, min_score_first)
    if len(shortlist) < 3 and len(state.candidates) >= 3:
        state.needs_disambiguination = True  # backwards typo tolerance
        state.needs_disambiguation = True
        shortlist = _shortlist(state.jd, state.candidates, top_n_wide, min_score_first * widen_factor)
        if len(shortlist) < 3:
            scored = sorted(state.candidates, key=lambda x: getattr(x, "score", 0.0), reverse=True)
            shortlist = scored[:min(3, len(scored))]
    state.shortlisted = shortlist
    TRACER.log_node("Analyst", "done", shortlisted=len(state.shortlisted), widened=bool(getattr(state, "needs_disambiguation", False)))
    return state

def question_writer(
    state: OrchestratorState,
    *,
    csv_path: str = "data/question_bank.csv",
    top_k_retrieve: int = 16,
    target_min: int = 8,
    target_max: int = 12,
    model: str = "gpt-4o-mini"
) -> OrchestratorState:
    TRACER.log_node("QuestionWriter", "start", jd_title=state.jd.title)
    kb = LocalQuestionBank(csv_path)
    query = build_query_from_jd(state.jd)
    retrieved = kb.search(query, top_k=top_k_retrieve)

    try:
        client = OpenAI()
        sys = (
            "You are an expert interviewer. Rewrite the provided questions so they are:\n"
            f"- tailored to the role '{state.jd.title}' and must-have skills {state.jd.must_haves}\n"
            f"- return ONLY {target_min} to {target_max} questions, one per line, no numbering\n"
            "Do not invent details beyond the JD."
        )
        user = "Base questions:\n" + "\n".join(f"- {q}" for q in retrieved)
        resp = client.chat.completions.create(
            model=model, temperature=0.2,
            messages=[{"role":"system","content":sys},{"role":"user","content":user}],
        )
        content = (resp.choices[0].message.content or "").strip()
        lines = [l.strip().lstrip("-").strip() for l in content.split("\n")]
        lines = [l for l in lines if len(l) > 5]
        seen = set(); tailored: List[str] = []
        for q in lines:
            key = q.lower()
            if key not in seen:
                seen.add(key); tailored.append(q)
        # Top-up / trim
        for q in retrieved:
            if len(tailored) >= target_min: break
            k = q.lower()
            if k not in seen:
                seen.add(k); tailored.append(q)
        if len(tailored) > target_max:
            tailored = tailored[:target_max]
        state.questions = tailored
    except Exception as e:
        # Fallback: use retrieved directly
        seen = set(); fb: List[str] = []
        for q in retrieved:
            k = q.lower()
            if k not in seen:
                seen.add(k); fb.append(q)
            if len(fb) >= target_max: break
        state.questions = fb[:max(target_min, min(target_max, len(fb)))]
        TRACER.log_node("QuestionWriter", "fallback", reason=str(e)[:120])

    ok, errs = validate_state_transition(state)
    state.schema_ok = ok
    if not ok:
        state.violations.extend(errs)
    TRACER.log_node("QuestionWriter", "done", n_questions=len(state.questions), schema_ok=state.schema_ok)
    return state

def reviewer(state: OrchestratorState) -> OrchestratorState:
    """
    Repair invalid structure without inventing facts:
    - ensure 8..12 distinct, non-empty questions (derive from JD if needed)
    - ensure shortlist has at least 1 candidate if any were parsed
    """
    TRACER.log_node("Reviewer", "start")
    # Questions: dedupe & trim; if <8, derive from JD.must_haves
    q_clean = []
    seen = set()
    for q in state.questions:
        if isinstance(q, str):
            q2 = q.strip()
            if q2:
                k = q2.lower()
                if k not in seen:
                    seen.add(k); q_clean.append(q2)
    # Top up from JD.must_haves
    i = 0
    while len(q_clean) < 8 and i < len(state.jd.must_haves):
        skill = state.jd.must_haves[i].strip()
        if skill:
            q_clean.append(f"Can you share a recent example using {skill}?")
        i += 1
    state.questions = q_clean[:12]

    # Shortlist: if empty but candidates exist, pick the best 1 by score
    if not state.shortlisted and state.candidates:
        best = sorted(state.candidates, key=lambda x: getattr(x, "score", 0.0), reverse=True)[:1]
        state.shortlisted = best

    ok, errs = validate_state_transition(state)
    state.schema_ok = ok
    if not ok:
        state.violations.extend(errs)

    # Final pass: validate final output for artifact
    final_ok, final_errs = validate_final_output(state)
    state.schema_ok = final_ok
    if not final_ok:
        state.violations.extend(final_errs)

    TRACER.log_node("Reviewer", "done", schema_ok=state.schema_ok, violations=len(state.violations))
    return state
