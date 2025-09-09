# src/tools/parser.py
from __future__ import annotations
import os, re, json
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError
from pypdf import PdfReader
from docx import Document
from openai import OpenAI

from src.state import JD, Candidate

# ---------- File loading ----------

from pathlib import Path
from pypdf import PdfReader
from docx import Document

def load_text(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in {".txt", ".md", ".markdown"}:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return _clean(f.read())
    if ext == ".pdf":
        reader = PdfReader(path)
        pages = []
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or "")
            except Exception:
                pages.append("")
        return _clean("\n".join(pages))
    if ext == ".docx":
        doc = Document(path)
        return _clean("\n".join(p.text for p in doc.paragraphs))
    # last-resort: try to read as plain text
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return _clean(f.read())
    except Exception:
        raise ValueError(f"Unsupported file type: {ext}")


def _clean(text: str) -> str:
    # Normalize whitespace and strip control chars
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

# ---------- OpenAI JSON helper ----------

class JsonParseError(RuntimeError): ...
class OpenAIError(RuntimeError): ...

def _client() -> OpenAI:
    # OPENAI_API_KEY is read from env
    return OpenAI(api_key="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")

@retry(
    stop=stop_after_attempt(2),                     # 1 try + 1 retry
    wait=wait_exponential(min=1, max=8),
    retry=retry_if_exception_type((JsonParseError, OpenAIError)),
    reraise=True,
)
def _chat_json(system: str, user: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Call OpenAI chat in JSON mode; raise if JSON can't be parsed.
    """
    try:
        resp = _client().chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user",    "content": user},
            ],
        )
    except Exception as e:
        raise OpenAIError(str(e)) from e

    try:
        content = resp.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        # Force a retry with a stricter instruction on second attempt
        raise JsonParseError("Model did not return valid JSON") from e

# ---------- JD / Resume extraction ----------

def parse_jd_to_struct(text: str) -> JD:
    """
    Returns JD(title, must_haves>=3 ideally, nice_haves, location?).
    """
    system = (
        "You extract a JSON object with fields: "
        "title (string), must_haves (array of 3-8 concise skill strings), "
        "nice_haves (array of 0-8 skill strings), location (string|null). "
        "Never invent facts; if unknown, set to null or empty list. Return ONLY JSON."
    )
    user = f"JD text:\n{text}"
    data = _chat_json(system, user)
    # Safety fix-ups
    data.setdefault("must_haves", [])
    data.setdefault("nice_haves", [])
    # Ensure list types
    data["must_haves"] = [s.strip() for s in data["must_haves"] if isinstance(s, str) and s.strip()]
    data["nice_haves"] = [s.strip() for s in data["nice_haves"] if isinstance(s, str) and s.strip()]
    # Construct JD or raise validation error (caught by caller if desired)
    return JD(**{
        "title": data.get("title") or "Unknown Role",
        "must_haves": data["must_haves"] or ["General problem solving"],
        "nice_haves": data["nice_haves"],
        "location": data.get("location"),
    })

def parse_resume_to_struct(text: str, path: str) -> Candidate:
    """
    Returns Candidate(name, email?, years_exp, skills[]).
    """
    system = (
        "Extract a JSON object with fields: "
        "name (string), email (string|null), years_exp (integer >=0), "
        "skills (array of 3-15 concise skill strings). "
        "Never invent employment history; if unknown use defaults. Return ONLY JSON."
    )
    user = f"Resume text:\n{text}"
    data = _chat_json(system, user)
    # Post-process
    email = data.get("email")
    if email and not re.search(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(email)):
        email = None  # drop weird emails
    years = data.get("years_exp") or 0
    try:
        years = int(years)
        if years < 0: years = 0
    except Exception:
        years = 0
    skills = [s.strip() for s in (data.get("skills") or []) if isinstance(s, str) and s.strip()]
    name = (data.get("name") or "Unknown").strip() or "Unknown"

    return Candidate(
        name=name,
        email=email,
        years_exp=years,
        skills=skills[:15],
        resume_path=path,
    )

def parse_resumes_from_dir(res_dir: str) -> List[Candidate]:
    out: List[Candidate] = []
    for fn in os.listdir(res_dir):
        path = os.path.join(res_dir, fn)
        if not os.path.isfile(path):
            continue
        if os.path.splitext(path)[1].lower() not in {".txt", ".pdf", ".docx"}:
            continue
        txt = load_text(path)
        out.append(parse_resume_to_struct(txt, path))
    return out
