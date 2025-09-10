"""
HTML report generation for HR Interview Orchestrator.
Creates professional, human-readable reports for HR teams.
"""
from jinja2 import Template
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import json

from src.state import OrchestratorState, Candidate
from src.config import config

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interview Report - {{jd_title}}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
            margin: 0;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 600;
        }
        
        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            color: #2c3e50;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
        }
        
        .job-info {
            background: #e8f4fd;
            padding: 20px;
            border-radius: 8px;
            border-left: 5px solid #3498db;
            margin-bottom: 30px;
        }
        
        .job-info h3 {
            color: #2980b9;
            margin-bottom: 15px;
        }
        
        .skills-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        
        .skill-tag {
            background: #3498db;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
        }
        
        .skill-tag.nice-have {
            background: #95a5a6;
        }
        
        .candidates-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .candidate {
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .candidate:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        }
        
        .candidate.scheduled {
            border-left: 5px solid #27ae60;
            background: #f8fff8;
        }
        
        .candidate.waitlist {
            border-left: 5px solid #f39c12;
            background: #fffdf8;
        }
        
        .candidate.low-score {
            border-left: 5px solid #e74c3c;
            background: #fdf8f8;
        }
        
        .candidate-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .candidate-name {
            font-size: 1.3em;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .candidate-score {
            font-size: 1.5em;
            font-weight: bold;
            padding: 5px 15px;
            border-radius: 25px;
            color: white;
            margin-left: auto;
        }
        
        .score-excellent { background: #27ae60; }
        .score-good { background: #f39c12; }
        .score-poor { background: #e74c3c; }
        
        .candidate-details {
            margin-bottom: 15px;
        }
        
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        
        .detail-label {
            font-weight: 600;
            color: #7f8c8d;
        }
        
        .detail-value {
            color: #2c3e50;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: 600;
            text-align: center;
            margin-top: 10px;
        }
        
        .status-scheduled {
            background: #d5f4e6;
            color: #27ae60;
        }
        
        .status-waitlist {
            background: #fef9e7;
            color: #f39c12;
        }
        
        .status-not-selected {
            background: #fadbd8;
            color: #e74c3c;
        }
        
        .questions-list {
            counter-reset: question-counter;
        }
        
        .question-item {
            counter-increment: question-counter;
            background: #f8f9fa;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
            position: relative;
        }
        
        .question-item::before {
            content: counter(question-counter);
            position: absolute;
            left: -20px;
            top: 15px;
            background: #3498db;
            color: white;
            width: 25px;
            height: 25px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.9em;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-top: 4px solid #3498db;
        }
        
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .metric-label {
            color: #7f8c8d;
            font-weight: 500;
        }
        
        .footer {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            margin-top: 40px;
        }
        
        .no-print {
            margin-top: 20px;
        }
        
        @media print {
            .no-print { display: none; }
            body { background: white; }
            .container { box-shadow: none; }
        }
        
        @media (max-width: 768px) {
            .candidates-grid {
                grid-template-columns: 1fr;
            }
            .candidate-header {
                flex-direction: column;
                align-items: flex-start;
            }
            .candidate-score {
                margin-left: 0;
                margin-top: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Interview Report</h1>
            <div class="subtitle">{{company_name}} • Generated {{timestamp}}</div>
        </div>
        
        <div class="content">
            <!-- Job Information -->
            <div class="job-info">
                <h3>📄 {{jd_title}}</h3>
                <div class="detail-row">
                    <span class="detail-label">Location:</span>
                    <span class="detail-value">{{location or 'Remote/Not specified'}}</span>
                </div>
                
                <div style="margin-top: 15px;">
                    <strong>Required Skills:</strong>
                    <div class="skills-container">
                        {% for skill in must_haves %}
                        <span class="skill-tag">{{skill}}</span>
                        {% endfor %}
                    </div>
                </div>
                
                {% if nice_haves %}
                <div style="margin-top: 15px;">
                    <strong>Preferred Skills:</strong>
                    <div class="skills-container">
                        {% for skill in nice_haves %}
                        <span class="skill-tag nice-have">{{skill}}</span>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
            </div>
            
            <!-- Candidates Section -->
            <div class="section">
                <h2>🏆 Candidate Rankings</h2>
                <div class="candidates-grid">
                    {% for candidate in shortlisted %}
                    {% set score_pct = (candidate.score * 100) | round(1) %}
                    <div class="candidate 
                        {% if loop.index <= schedule_count %}scheduled
                        {% elif score_pct >= 40 %}waitlist
                        {% else %}low-score{% endif %}">
                        
                        <div class="candidate-header">
                            <div class="candidate-name">{{candidate.name}}</div>
                            <div class="candidate-score 
                                {% if score_pct >= 70 %}score-excellent
                                {% elif score_pct >= 40 %}score-good
                                {% else %}score-poor{% endif %}">
                                {{score_pct}}%
                            </div>
                        </div>
                        
                        <div class="candidate-details">
                            <div class="detail-row">
                                <span class="detail-label">Email:</span>
                                <span class="detail-value">{{candidate.email or '❌ Not found'}}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Experience:</span>
                                <span class="detail-value">{{candidate.years_exp}} years</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Skills Count:</span>
                                <span class="detail-value">{{candidate.skills|length}} skills</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Raw Score:</span>
                                <span class="detail-value">{{candidate.score|round(3)}}</span>
                            </div>
                        </div>
                        
                        {% if candidate.skills %}
                        <div style="margin-top: 15px;">
                            <strong>Skills:</strong>
                            <div class="skills-container" style="margin-top: 8px;">
                                {% for skill in candidate.skills[:8] %}
                                <span class="skill-tag" style="background: #95a5a6; font-size: 0.8em;">{{skill}}</span>
                                {% endfor %}
                                {% if candidate.skills|length > 8 %}
                                <span style="color: #7f8c8d; font-size: 0.9em;">+{{candidate.skills|length - 8}} more</span>
                                {% endif %}
                            </div>
                        </div>
                        {% endif %}
                        
                        <div class="status-badge 
                            {% if loop.index <= schedule_count %}status-scheduled
                            {% elif score_pct >= 40 %}status-waitlist
                            {% else %}status-not-selected{% endif %}">
                            {% if loop.index <= schedule_count %}
                                📅 Interview Scheduled
                            {% elif score_pct >= 40 %}
                                ⏸️ On Waitlist
                            {% else %}
                                ❌ Not Selected
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Interview Questions -->
            <div class="section">
                <h2>❓ Interview Questions ({{questions|length}} total)</h2>
                <div class="questions-list">
                    {% for question in questions %}
                    <div class="question-item">{{question}}</div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Metrics -->
            <div class="section">
                <h2>📊 Process Metrics</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{{metrics.num_candidates}}</div>
                        <div class="metric-label">Candidates Processed</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{shortlisted|length}}</div>
                        <div class="metric-label">Shortlisted</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{schedule_count}}</div>
                        <div class="metric-label">Interviews Scheduled</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{metrics.elapsed_seconds|round(1)}}s</div>
                        <div class="metric-label">Processing Time</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{questions|length}}</div>
                        <div class="metric-label">Questions Generated</div>
                    </div>
                    {% if metrics.needed_widening %}
                    <div class="metric-card" style="border-top-color: #f39c12;">
                        <div class="metric-value">⚠️</div>
                        <div class="metric-label">Search Widened</div>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by HR Interview Orchestrator • {{company_name}}</p>
            <div class="no-print">
                <p style="margin-top: 10px; font-size: 0.9em; opacity: 0.8;">
                    💡 This report is also available in JSON format for programmatic access
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

def generate_html_report(
    state: OrchestratorState, 
    metrics: Dict[str, Any], 
    schedule_count: int = 2,
    output_path: str = None
) -> str:
    """
    Generate a comprehensive HTML report for the interview process.
    
    Args:
        state: The orchestrator state with candidates and job info
        metrics: Processing metrics and timing information
        schedule_count: Number of candidates scheduled for interviews
        output_path: Optional custom output path
    
    Returns:
        Path to the generated HTML report
    """
    if output_path is None:
        output_path = config.ARTIFACTS_DIR / "interview_report.html"
    
    template = Template(HTML_TEMPLATE)
    
    html_content = template.render(
        jd_title=state.jd.title,
        company_name=config.COMPANY_NAME,
        location=state.jd.location,
        must_haves=state.jd.must_haves,
        nice_haves=state.jd.nice_haves,
        shortlisted=state.shortlisted,
        questions=state.questions,
        metrics=metrics,
        schedule_count=schedule_count,
        timestamp=datetime.now().strftime("%B %d, %Y at %I:%M %p")
    )
    
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Write the HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return str(output_path)

def generate_summary_report(
    state: OrchestratorState,
    metrics: Dict[str, Any],
    artifacts: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a structured summary report for JSON output.
    
    Returns:
        Enhanced JSON report with human-readable summaries
    """
    # Calculate summary statistics
    total_candidates = len(state.candidates)
    shortlisted_count = len(state.shortlisted)
    scheduled_count = min(shortlisted_count, config.SCHEDULE_TOP_N)
    
    # Score distribution
    if state.shortlisted:
        avg_score = sum(c.score for c in state.shortlisted) / len(state.shortlisted)
        max_score = max(c.score for c in state.shortlisted)
        min_score = min(c.score for c in state.shortlisted)
    else:
        avg_score = max_score = min_score = 0.0
    
    # Enhanced candidate summaries
    candidate_summaries = []
    for i, candidate in enumerate(state.shortlisted, 1):
        summary = {
            "rank": i,
            "name": candidate.name,
            "email": candidate.email,
            "score": round(candidate.score, 3),
            "match_percentage": round(candidate.score * 100, 1),
            "years_experience": candidate.years_exp,
            "skills_count": len(candidate.skills),
            "skills": candidate.skills,
            "status": "scheduled" if i <= scheduled_count else "waitlisted",
            "has_email": bool(candidate.email)
        }
        candidate_summaries.append(summary)
    
    return {
        "job_description": {
            "title": state.jd.title,
            "location": state.jd.location,
            "required_skills": state.jd.must_haves,
            "preferred_skills": state.jd.nice_haves
        },
        "process_summary": {
            "total_candidates_processed": total_candidates,
            "candidates_shortlisted": shortlisted_count,
            "interviews_scheduled": scheduled_count,
            "questions_generated": len(state.questions),
            "processing_time_seconds": metrics.get("elapsed_seconds", 0),
            "search_widened": metrics.get("needed_widening", False)
        },
        "scoring_statistics": {
            "average_score": round(avg_score, 3),
            "highest_score": round(max_score, 3),
            "lowest_score": round(min_score, 3),
            "threshold_used": config.MIN_SCORE_THRESHOLD
        },
        "candidates": candidate_summaries,
        "interview_questions": state.questions,
        "artifacts_generated": {
            "html_report": True,
            "email_drafts": len(artifacts.get("emails", [])),
            "calendar_invites": len(artifacts.get("invites", [])),
            "gmail_drafts": len(artifacts.get("gmail_drafts", []))
        },
        "generated_at": datetime.now().isoformat(),
        "company": config.COMPANY_NAME
    }
