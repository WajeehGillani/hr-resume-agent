# HR Interview Orchestrator 🎯

**AI-Powered Candidate Screening & Interview Automation**

A comprehensive LangGraph-based system that automates HR interview processes from job description parsing to candidate shortlisting, question generation, and interview scheduling.

## ✨ Features

### 🔍 **Intelligent Candidate Analysis**

- **Smart Parsing**: Extracts structured data from any JD format (PDF, Word, Markdown)
- **AI-Powered Scoring**: Multi-factor candidate evaluation with configurable weights
- **Skill Matching**: Advanced overlap detection with fuzzy matching
- **Experience Weighting**: Years of experience factor in scoring

### 📊 **Professional Output**

- **Rich Console Interface**: Beautiful progress bars and colorized output
- **HTML Reports**: Professional, print-ready interview reports
- **Enhanced JSON**: Comprehensive candidate analytics and insights
- **Multiple Formats**: Choose between JSON, HTML, or both

### 📧 **Communication Automation**

- **Professional Email Templates**: Customizable interview invitations
- **Gmail Integration**: Automatic draft creation in your Gmail account
- **Calendar Management**: ICS files + optional Google Calendar events
- **PII Protection**: Automatic redaction of sensitive information

### 🛡️ **Enterprise-Ready**

- **Offline Mode**: Works without API keys using deterministic algorithms
- **Configuration System**: Environment-based settings with validation
- **Error Handling**: Robust failover and retry mechanisms
- **Security**: No hardcoded credentials, proper secret management

## 🚀 Quick Start

### 1. Installation

```bash
git clone <repository>
cd hr-interview-orchestrator
python -m pip install -r requirements.txt
```

### 2. Configuration (Optional)

Copy the example configuration:

```bash
cp env.example .env
```

Edit `.env` with your settings:

```env
# OpenAI for enhanced parsing (optional)
OPENAI_API_KEY=your_openai_api_key_here

# Company branding
COMPANY_NAME=Your Company Name
EMAIL_FROM=hr@yourcompany.com

# Scoring preferences
SCHEDULE_TOP_N=2
INTERVIEW_DURATION_MINUTES=45
```

### 3. Run the Application

```bash
python -m src.graph --jd data/sample_jd.md --resumes data/resumes
```

### 4. Try the Interactive Demo (Optional)

Explore the system with our Jupyter notebook demo:

```bash
cd notebooks
pip install -r requirements.txt
jupyter notebook demo.ipynb
```

The notebook provides an interactive walkthrough of all features with sample data.

**Command Options:**

- `--output-format [json|html|both]` - Choose output format (default: both)
- `--when "2025-09-15T10:00:00"` - Schedule interview time
- `--quiet` - Minimal console output
- `--no-progress` - Disable progress bars
- `--validate-jd` - Validate job description quality using internal MCP tool
- `--parse-jd-only` - Only parse job description and exit (MCP tool demo)

## 📁 Output Structure

After processing, check the organized `artifacts/` folder:

```
artifacts/
├── latest/                           # Quick access to most recent run
│   ├── emails/
│   ├── calendars/
│   ├── reports/
│   │   ├── results.json             # Comprehensive JSON results
│   │   └── interview_report.html    # Professional HTML report
│   └── run_summary.json             # Run metadata
├── runs/                            # All historical runs organized by timestamp
│   ├── 20250910_143022_mern_stack_developer/
│   │   ├── emails/
│   │   │   ├── 01_john_doe.eml      # Candidate-specific emails
│   │   │   └── 02_jane_smith.eml
│   │   ├── calendars/
│   │   │   ├── 01_john_doe.ics      # Candidate-specific invites
│   │   │   └── 02_jane_smith.ics
│   │   ├── reports/
│   │   │   ├── results.json         # Comprehensive results
│   │   │   └── interview_report.html # Professional report
│   │   ├── logs/
│   │   │   └── execution_*.jsonl    # Detailed execution logs
│   │   └── run_summary.json         # Run metadata
│   └── 20250909_091234_backend_engineer/  # Previous runs...
├── cache/                           # Persistent cache (embeddings, models)
│   ├── faiss_qbank/                # Question bank embeddings
│   └── embeddings_cache.npy        # Cached embeddings
└── runs_index.json                 # Index of all runs with metadata
```

### 🗂️ **Smart File Organization**

- **Timestamped Runs**: Each execution creates a timestamped folder
- **Quick Access**: `latest/` symlink points to most recent run
- **Clean Structure**: Emails, calendars, reports organized separately
- **Persistent Cache**: Embeddings and models cached separately
- **Easy Cleanup**: Built-in cleanup utilities

### Sample Enhanced Output

```json
{
  "job_description": {
    "title": "MERN Stack Developer",
    "required_skills": ["React", "Node.js", "MongoDB", "Express"],
    "location": "Remote"
  },
  "process_summary": {
    "total_candidates_processed": 7,
    "candidates_shortlisted": 3,
    "interviews_scheduled": 2,
    "processing_time_seconds": 12.4
  },
  "candidates": [
    {
      "rank": 1,
      "name": "Sarah Johnson",
      "score": 0.847,
      "match_percentage": 84.7,
      "status": "scheduled",
      "skills": ["React", "TypeScript", "Node.js", "MongoDB"]
    }
  ]
}
```

## 🔧 Google Integration

### Gmail & Calendar Setup

1. **Create OAuth Credentials**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create OAuth 2.0 Client ID (Desktop application)
   - Download the JSON file

2. **Configure Integration**:

   ```bash
   # Option 1: Place files at project root
   cp /path/to/client_secret.json credentials.json
   cp /path/to/token.json token.json

   # Option 2: Use environment variables
   export GOOGLE_CLIENT_SECRET_FILE="/path/to/credentials.json"
   export GOOGLE_TOKEN_FILE="/path/to/token.json"
   ```

3. **Enable Features**:
   ```env
   USE_REAL_CALENDAR=1
   ```

**What it does:**

- ✅ Creates Gmail drafts for interview invitations
- ✅ Adds tentative calendar events to your Google Calendar
- ✅ Falls back to ICS files if integration fails

## 🔗 LangSmith Integration

**LangSmith** provides comprehensive tracing, evaluation, and monitoring for the AI-powered components.

### Setup

1. **Get LangSmith API Key**:

   - Sign up at [LangSmith](https://smith.langchain.com/)
   - Get your API key from the settings

2. **Configure Integration**:
   ```env
   LANGSMITH_API_KEY=your_langsmith_api_key_here
   LANGSMITH_PROJECT=hr-interview-orchestrator
   LANGSMITH_TRACING=1
   ```

### Features

- **🔍 Comprehensive Tracing**: Every LLM call, agent decision, and tool use is traced
- **📊 Performance Monitoring**: Track processing times, token usage, and success rates
- **📈 Evaluation Datasets**: Automatically create datasets from successful runs
- **🎯 Quality Insights**: Monitor parsing accuracy, scoring consistency, and question quality
- **📋 Run Comparison**: Compare different runs to optimize performance

### What Gets Traced

- **JD Parsing**: Success rate and accuracy of job requirement extraction
- **Candidate Scoring**: Individual candidate analysis and scoring decisions
- **Question Generation**: Quality and relevance of generated interview questions
- **Full Pipeline**: End-to-end run performance and bottlenecks

## 🔧 Internal MCP Tool

The system includes an internal **MCP-compatible job description parsing tool** for enhanced functionality:

### Features

- **📄 Job Description Parsing**: Extract structured data from any JD format
- **📊 Quality Validation**: Assess JD completeness and provide improvement suggestions
- **🎯 Standards Compliance**: MCP tool schema for potential external integration
- **⚡ Internal Use**: Optimized for internal workflow integration

### Usage Examples

**Parse job description only:**

```bash
python -m src.graph --jd data/sample_jd.md --resumes data/resumes --parse-jd-only
```

**Validate JD quality:**

```bash
python -m src.graph --jd data/sample_jd.md --resumes data/resumes --validate-jd
```

**Internal Python usage:**

```python
from src.tools.mcp_tool import parse_job_description_internal, validate_job_description_quality

# Parse JD to structured data
data = parse_job_description_internal(jd_text)
print(f"Found {len(data['must_haves'])} requirements")

# Validate quality
quality = validate_job_description_quality(jd_text)
print(f"Quality score: {quality['quality_score']}/100")
```

### Quality Assessment

The tool evaluates JD quality based on:

- **Title clarity** (20 points)
- **Location specification** (10 points)
- **Required skills** (40 points)
- **Preferred skills** (15 points)
- **Content detail** (15 points)

Scores: 80+ = Excellent, 60+ = Good, 40+ = Fair, <40 = Needs Improvement

## 🎯 Advanced Configuration

### Scoring Customization

```env
# Adjust scoring weights and thresholds
MIN_SCORE_THRESHOLD=0.35
TOP_CANDIDATES_COUNT=5
SCHEDULE_TOP_N=2

# Interview settings
INTERVIEW_DURATION_MINUTES=45
DEFAULT_LOCATION=Google Meet
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=17
```

### Company Branding

```env
COMPANY_NAME=Acme Corporation
EMAIL_FROM=talent@acme.com
COMPANY_WEBSITE=https://acme.com
```

## 📊 Candidate Scoring Algorithm

The system uses a **multi-factor scoring model**:

```
Final Score = 0.7 × Must-Have Match + 0.2 × Nice-to-Have Match + 0.1 × Experience Bonus

Where:
- Must-Have Match = (Matched Skills / Total Required Skills)
- Nice-to-Have Match = (Matched Preferred Skills / Total Preferred Skills)
- Experience Bonus = min(Years Experience / 10, 0.3)
```

**Example Calculation:**

- Required: ["React", "Node.js", "MongoDB"] (3 skills)
- Candidate has: ["React", "Node.js", "Python"] (2 matches)
- Experience: 5 years
- Score: 0.7 × (2/3) + 0.2 × 0 + 0.1 × 0.3 = **0.497**

## 🛠️ Development & Customization

### Adding Custom Email Templates

Edit `src/templates.py`:

```python
EMAIL_TEMPLATES["custom_invite"] = {
    "subject": "Custom Subject - {jd_title}",
    "body": "Custom email body with {candidate_name}..."
}
```

### Custom Scoring Logic

Modify `src/agents.py` in the `_score_candidate` function:

```python
def _score_candidate(jd: JD, c: Candidate) -> float:
    # Your custom scoring logic here
    return custom_score
```

### Question Bank Management

Update `data/question_bank.csv`:

```csv
role,question
MERN Developer,How do you handle state management in React?
Backend Engineer,Explain your approach to API design
```

## 🔍 Troubleshooting

### Common Issues

**"No candidates found"**

- Check resume directory path
- Ensure files are .pdf, .docx, or .txt format
- Verify files aren't corrupted

**"General problem solving" in must-haves**

- Set `OPENAI_API_KEY` for better parsing
- Check JD format has clear "Must-haves" section
- Try different JD file format

**Google integration not working**

- Verify credentials.json is valid
- Check OAuth scopes include calendar and gmail
- Ensure USE_REAL_CALENDAR=1 is set

### Performance Tips

- Use OpenAI API key for fastest parsing
- Place resumes in dedicated folder (avoid large files)
- Enable HTML reports only when needed
- Use `--quiet` flag for automated runs

## 🧹 Artifact Management

### Automatic Organization

Every run creates an organized directory structure with:

- Timestamped folders for easy identification
- Separate subdirectories for emails, calendars, reports
- Quick access via `artifacts/latest/` symlink
- Persistent cache for embeddings and models

### Cleanup Utilities

**List recent runs:**

```bash
python cleanup.py --list-runs
```

**Clean up old files (keep 10 latest runs):**

```bash
python cleanup.py
```

**Aggressive cleanup (keep only 3 runs):**

```bash
python cleanup.py --aggressive
```

**Custom cleanup:**

```bash
python cleanup.py --keep-runs 5    # Keep 5 latest runs
python cleanup.py --dry-run        # See what would be cleaned
```

### File Organization Benefits

- **No More Clutter**: Organized structure prevents artifact folder chaos
- **Easy Navigation**: Find any run by timestamp and job title
- **Quick Access**: Always know where the latest results are
- **Historical Archive**: Keep track of all previous runs
- **Efficient Storage**: Cache shared across runs to save space

## 📝 Requirements

- **Python 3.8+**
- **Dependencies**: See `requirements.txt`
- **Optional**: OpenAI API key for enhanced parsing
- **Optional**: Google OAuth for Gmail/Calendar integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Made with ❤️ for HR teams who want to focus on connecting with great candidates, not managing spreadsheets.**
