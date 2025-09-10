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

def _client() -> OpenAI | None:
    # Return client only if API key available; else None for offline fallback
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.strip() and not api_key.startswith("your_"):
        try:
            return OpenAI()  # Reads OPENAI_API_KEY from environment automatically
        except Exception:
            # If client creation fails (invalid key, etc.), return None for fallback
            return None
    return None

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
    client = _client()
    if client is None:
        raise OpenAIError("OPENAI_API_KEY not set; skipping online parse")
    try:
        resp = client.chat.completions.create(
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
    Uses OpenAI LLM for robust extraction from any JD format.
    """
    system = (
        "You are a job description parser. Extract structured data from the provided job description text.\n\n"
        "Instructions:\n"
        "- Extract the job title, removing any company prefix (e.g., 'Job:', 'Position:', '#')\n"
        "- Find required skills/technologies (must-haves, requirements, qualifications)\n"
        "- Find preferred skills/technologies (nice-to-haves, preferred, bonus)\n"
        "- Extract location if mentioned\n"
        "- Return concise skill names (e.g., 'React', 'Node.js', 'Python')\n"
        "- Don't invent skills not mentioned in the text\n\n"
        "Return a JSON object with exactly these fields:\n"
        "{\n"
        '  "title": "string - clean job title",\n'
        '  "must_haves": ["array", "of", "required", "skills"],\n'
        '  "nice_haves": ["array", "of", "preferred", "skills"],\n'
        '  "location": "string or null"\n'
        "}\n\n"
        "Return ONLY the JSON object, no other text."
    )
    
    user = f"Job Description:\n\n{text}"
    
    try:
        data = _chat_json(system, user)
        
        # Clean and validate extracted data
        title = (data.get("title") or "").strip()
        if not title or len(title) < 2:
            title = "Unknown Role"
            
        must_haves = data.get("must_haves", [])
        if not isinstance(must_haves, list):
            must_haves = []
        must_haves = [s.strip() for s in must_haves if isinstance(s, str) and s.strip()]
        
        nice_haves = data.get("nice_haves", [])
        if not isinstance(nice_haves, list):
            nice_haves = []
        nice_haves = [s.strip() for s in nice_haves if isinstance(s, str) and s.strip()]
        
        location = data.get("location")
        if location and not isinstance(location, str):
            location = None
            
        # Ensure we have at least some must-haves
        if not must_haves:
            must_haves = ["General problem solving"]
        
        return JD(
            title=title,
            must_haves=must_haves[:8],  # Limit to 8
            nice_haves=nice_haves[:8],  # Limit to 8
            location=location
        )
        
    except Exception as e:
        # Enhanced offline fallback for when OpenAI API is not available
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = "Unknown Role"
        must_haves = []
        nice_haves = []
        location = None
        
        # Extract title (look for headings with job roles)
        for line in lines[:10]:
            if any(word in line.lower() for word in ["developer", "engineer", "manager", "analyst", "designer", "architect", "lead", "senior"]):
                title = re.sub(r"^[#\-\*\s]*", "", line).strip()
                if ":" in title:
                    title = title.split(":", 1)[1].strip()
                break
        
        # Extract location
        location_keywords = ["location", "remote", "hybrid", "office"]
        for line in lines:
            if any(keyword in line.lower() for keyword in location_keywords) and (":" in line or "," in line):
                location = line.split(":", 1)[-1].split(",")[-1].strip()
                break
        
        # Extract skills from must-have and nice-to-have sections
        in_must_section = False
        in_nice_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect section headers
            if any(header in line_lower for header in ["must-have", "must have", "requirements", "required", "qualifications"]):
                in_must_section = True
                in_nice_section = False
                continue
            elif any(header in line_lower for header in ["nice-to-have", "nice to have", "preferred", "bonus", "optional"]):
                in_nice_section = True
                in_must_section = False
                continue
            elif any(header in line_lower for header in ["responsibilities", "about", "interview", "experience"]) and not any(skill in line_lower for skill in ["python", "react", "node"]):
                in_must_section = False
                in_nice_section = False
                continue
            
            # Extract skills from current section
            if in_must_section or in_nice_section:
                # Remove markdown formatting and bullets
                cleaned = re.sub(r"^\s*[-*•]\s*", "", line)
                cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)  # Remove **bold**
                
                # Extract individual skills
                if cleaned and len(cleaned) > 3:
                    # Look for parenthetical clarifications like "(hooks, routing)"
                    parens = re.findall(r"\((.*?)\)", cleaned)
                    for paren in parens:
                        skills_in_paren = [s.strip() for s in re.split(r"[,;]", paren) if s.strip()]
                        if in_must_section:
                            must_haves.extend(skills_in_paren)
                        else:
                            nice_haves.extend(skills_in_paren)
                    
                    # Extract main skills (removing parentheses)
                    main_line = re.sub(r"\([^)]*\)", "", cleaned).strip()
                    if main_line:
                        # Split on common delimiters
                        parts = re.split(r"[;,]\s*", main_line)
                        for part in parts:
                            part = part.strip()
                            if part and len(part) > 2:
                                if in_must_section:
                                    must_haves.append(part)
                                else:
                                    nice_haves.append(part)
        
        # Clean and deduplicate skills
        def clean_skills(skills_list):
            cleaned = []
            seen = set()
            for skill in skills_list:
                # Clean up the skill name
                clean = re.sub(r"^(and|with|for|using|in)\s+", "", skill, flags=re.I)
                clean = re.sub(r"\s+(and|with|for|using|in)$", "", clean, flags=re.I)
                clean = re.sub(r"[^\w\s\.\+\-#/]", "", clean).strip()
                
                if clean and len(clean) > 1 and clean.lower() not in seen:
                    seen.add(clean.lower())
                    cleaned.append(clean)
            return cleaned[:8]
        
        must_haves = clean_skills(must_haves)
        nice_haves = clean_skills(nice_haves)
        
        # If still no must-haves, try keyword extraction from the full text
        if not must_haves:
            tech_keywords = [
                "React", "Node.js", "Express", "MongoDB", "TypeScript", "JavaScript", "Python", 
                "Django", "Flask", "SQL", "PostgreSQL", "MySQL", "Redis", "Docker", "Kubernetes",
                "AWS", "Azure", "GCP", "Git", "Jest", "Redux", "Next.js", "Vue", "Angular"
            ]
            text_lower = text.lower()
            found_skills = []
            for keyword in tech_keywords:
                if keyword.lower() in text_lower:
                    found_skills.append(keyword)
            must_haves = found_skills[:6] if found_skills else ["General problem solving"]
                
        return JD(
            title=title[:100],
            must_haves=must_haves,
            nice_haves=nice_haves,
            location=location
        )

def parse_resume_to_struct(text: str, path: str) -> Candidate:
    """
    Returns Candidate(name, email?, years_exp, skills[]).
    Uses OpenAI LLM for robust extraction from any resume format.
    """
    system = (
        "You are a resume parser. Extract structured data from the provided resume text.\n\n"
        "Instructions:\n"
        "- Extract the candidate's full name\n"
        "- Find email address if present\n"
        "- Calculate total years of professional experience (not including education/internships)\n"
        "- Extract technical skills, programming languages, frameworks, tools\n"
        "- Return concise skill names (e.g., 'React', 'Python', 'AWS')\n"
        "- Don't invent information not in the resume\n\n"
        "Return a JSON object with exactly these fields:\n"
        "{\n"
        '  "name": "string - full name",\n'
        '  "email": "string or null - email address",\n'
        '  "years_exp": number - total years of experience,\n'
        '  "skills": ["array", "of", "technical", "skills"]\n'
        "}\n\n"
        "Return ONLY the JSON object, no other text."
    )
    
    user = f"Resume:\n\n{text}"
    
    try:
        data = _chat_json(system, user)
        
        # Clean and validate extracted data
        name = (data.get("name") or "").strip()
        if not name:
            # Try to extract from filename as fallback
            from pathlib import Path as _P
            name = _P(path).stem.replace("_", " ").replace("-", " ").strip().title() or "Unknown"
            
        email = data.get("email")
        if email and not re.search(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(email)):
            email = None
            
        years_exp = data.get("years_exp", 0)
        try:
            years_exp = int(years_exp) if years_exp is not None else 0
            years_exp = max(0, min(years_exp, 50))  # Clamp between 0-50
        except (ValueError, TypeError):
            years_exp = 0
            
        skills = data.get("skills", [])
        if not isinstance(skills, list):
            skills = []
        skills = [s.strip() for s in skills if isinstance(s, str) and s.strip()]
        
        return Candidate(
            name=name,
            email=email,
            years_exp=years_exp,
            skills=skills[:15],  # Limit to 15
            resume_path=path
        )
        
    except Exception:
        # Simple fallback
        from pathlib import Path as _P
        
        # Extract email
        email = None
        email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
        if email_match:
            email = email_match.group(0)
            
        # Extract name from filename
        name = _P(path).stem.replace("_", " ").replace("-", " ").strip().title() or "Unknown"
        
        # Simple years extraction
        years_exp = 0
        year_matches = re.findall(r"(\d{1,2})\s*\+?\s*years", text, re.I)
        if year_matches:
            years_exp = max([int(y) for y in year_matches if int(y) <= 50] or [0])
            
        return Candidate(
            name=name,
            email=email,
            years_exp=years_exp,
            skills=[],
            resume_path=path
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
