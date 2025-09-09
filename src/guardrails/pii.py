import re

def redact(t: str) -> str:
    t = re.sub(r"[\w\.-]+@[\w\.-]+", "[redacted-email]", t)
    t = re.sub(r"\+?\d[\d\-\s]{7,}\d", "[redacted-phone]", t)
    return t
