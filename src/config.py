"""
Configuration management for HR Interview Orchestrator.
Loads settings from environment variables and provides defaults.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

class Config:
    """Application configuration loaded from environment variables."""
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Google Integration
    GOOGLE_CLIENT_SECRET_FILE: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET_FILE")
    GOOGLE_CREDENTIALS_FILE: Optional[str] = os.getenv("GOOGLE_CREDENTIALS_FILE")
    GOOGLE_TOKEN_FILE: Optional[str] = os.getenv("GOOGLE_TOKEN_FILE")
    USE_REAL_CALENDAR: bool = os.getenv("USE_REAL_CALENDAR", "0") == "1"
    
    # Company Information
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "Wajeeh ul Hassan")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "hr@yourcompany.com")
    COMPANY_WEBSITE: str = os.getenv("COMPANY_WEBSITE", "https://yourcompany.com")
    
    # Scoring Configuration
    MIN_SCORE_THRESHOLD: float = float(os.getenv("MIN_SCORE_THRESHOLD", "0.35"))
    TOP_CANDIDATES_COUNT: int = int(os.getenv("TOP_CANDIDATES_COUNT", "3"))
    SCHEDULE_TOP_N: int = int(os.getenv("SCHEDULE_TOP_N", "2"))
    
    # Interview Settings
    INTERVIEW_DURATION_MINUTES: int = int(os.getenv("INTERVIEW_DURATION_MINUTES", "45"))
    DEFAULT_LOCATION: str = os.getenv("DEFAULT_LOCATION", "Google Meet")
    BUSINESS_HOURS_START: int = int(os.getenv("BUSINESS_HOURS_START", "9"))
    BUSINESS_HOURS_END: int = int(os.getenv("BUSINESS_HOURS_END", "17"))
    
    # Output Configuration
    OUTPUT_FORMATS: list = os.getenv("OUTPUT_FORMATS", "json,html").split(",")
    GENERATE_HTML_REPORT: bool = os.getenv("GENERATE_HTML_REPORT", "1") == "1"
    INCLUDE_REJECTION_EMAILS: bool = os.getenv("INCLUDE_REJECTION_EMAILS", "0") == "1"
    
    # Paths
    ARTIFACTS_DIR: Path = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    
    # LangSmith Configuration
    LANGSMITH_API_KEY: Optional[str] = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "hr-interview-orchestrator")
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "0") == "1"
    
    
    @classmethod
    def setup_directories(cls):
        """Ensure required directories exist."""
        cls.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate_required_config(cls) -> list[str]:
        """Check for missing required configuration and return list of issues."""
        issues = []
        
        if not cls.OPENAI_API_KEY:
            issues.append("⚠️  OPENAI_API_KEY not set - will use offline parsing")
        
        if cls.USE_REAL_CALENDAR and not (cls.GOOGLE_CLIENT_SECRET_FILE or cls.GOOGLE_CREDENTIALS_FILE):
            issues.append("⚠️  Google credentials not configured - calendar integration disabled")
        
        if cls.LANGSMITH_TRACING and not cls.LANGSMITH_API_KEY:
            issues.append("⚠️  LANGSMITH_API_KEY not set - tracing disabled")
        
        return issues

# Global config instance
config = Config()
