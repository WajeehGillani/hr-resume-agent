"""
Professional email and communication templates for HR Interview Orchestrator.
"""
from typing import Dict, Any
from datetime import datetime, timedelta
from src.config import config

EMAIL_TEMPLATES = {
    "interview_invite": {
        "subject": "Interview Invitation - {jd_title} at {company_name}",
        "body": """Dear {candidate_name},

Thank you for your interest in the {jd_title} position at {company_name}.

Based on your qualifications and experience, we would like to invite you for an interview to discuss this opportunity further.

📅 INTERVIEW DETAILS:
• Position: {jd_title}
• Date & Time: {interview_date}
• Duration: {duration} minutes
• Location: {location}
• Meeting Link: {meeting_link}

📋 INTERVIEW AGENDA:
• Technical discussion and problem-solving ({technical_duration} min)
• Experience and project walkthrough ({experience_duration} min)
• Company culture and role expectations ({culture_duration} min)
• Your questions and next steps ({qa_duration} min)

🎯 WHAT TO PREPARE:
• Be ready to discuss your experience with: {key_skills}
• Bring examples of relevant projects or work
• Prepare questions about the role and our company

Please confirm your availability by replying to this email by {response_deadline}. If this time doesn't work for you, please suggest 2-3 alternative times that would be convenient.

We're excited to learn more about your experience and discuss how you might contribute to our team!

Best regards,
{interviewer_name}
{company_name} Talent Acquisition Team

---
{company_name} | {company_website}
This email contains confidential information. If you received this in error, please delete it.
"""
    },
    
    "interview_reminder": {
        "subject": "Reminder: Interview Tomorrow - {jd_title}",
        "body": """Dear {candidate_name},

This is a friendly reminder about your upcoming interview for the {jd_title} position.

📅 INTERVIEW DETAILS:
• Date & Time: {interview_date}
• Duration: {duration} minutes
• Location: {location}
• Meeting Link: {meeting_link}

🔧 TECHNICAL SETUP:
• Please test your camera and microphone beforehand
• Ensure stable internet connection
• Have a backup phone number ready: {backup_contact}

📋 WHAT TO BRING:
• Your questions about the role and company
• Examples of relevant work or projects
• Notepad for taking notes

If you need to reschedule or have any technical issues, please contact us immediately at {contact_email} or {contact_phone}.

Looking forward to speaking with you tomorrow!

Best regards,
{interviewer_name}
{company_name} Team
"""
    },
    
    "rejection_polite": {
        "subject": "Update on your {jd_title} application - {company_name}",
        "body": """Dear {candidate_name},

Thank you for your interest in the {jd_title} position at {company_name} and for taking the time to apply.

After careful review of all applications, we have decided to move forward with other candidates whose experience more closely aligns with our current specific requirements.

This decision was not easy, as we received many strong applications. We were impressed by your background in {candidate_strengths}, and we encourage you to apply for future positions that may be a better match for your skills.

We will keep your information on file and may reach out if suitable opportunities arise in the next 6 months.

Thank you again for your interest in {company_name}. We wish you the best of luck in your job search.

Best regards,
{company_name} Talent Acquisition Team

---
{company_name} | {company_website}
"""
    },
    
    "follow_up_post_interview": {
        "subject": "Thank you - Next steps for {jd_title} position",
        "body": """Dear {candidate_name},

Thank you for taking the time to interview for the {jd_title} position yesterday. It was a pleasure speaking with you about your experience and learning more about your background.

📝 INTERVIEW RECAP:
We discussed your experience with {discussed_topics} and were particularly impressed by {positive_highlights}.

⏰ NEXT STEPS:
• We are completing interviews with all candidates this week
• We will make our decision by {decision_deadline}
• You can expect to hear from us by {communication_deadline}
• We will contact all candidates regardless of the outcome

❓ ADDITIONAL INFORMATION:
If you have any additional questions about the role or our company that came up after our conversation, please don't hesitate to reach out.

Thank you again for your interest in joining our team. We will be in touch soon.

Best regards,
{interviewer_name}
{company_name} Team
"""
    }
}

def format_interview_email(
    candidate_name: str,
    candidate_email: str,
    jd_title: str,
    interview_datetime: datetime,
    location: str = None,
    template_type: str = "interview_invite",
    **kwargs
) -> Dict[str, str]:
    """
    Format a professional interview email using templates.
    
    Args:
        candidate_name: Candidate's full name
        candidate_email: Candidate's email address
        jd_title: Job title
        interview_datetime: Scheduled interview date and time
        location: Interview location/platform
        template_type: Type of email template to use
        **kwargs: Additional template variables
    
    Returns:
        Dict with 'subject' and 'body' keys
    """
    if template_type not in EMAIL_TEMPLATES:
        template_type = "interview_invite"
    
    template = EMAIL_TEMPLATES[template_type]
    
    # Default values
    duration = kwargs.get("duration", config.INTERVIEW_DURATION_MINUTES)
    location = location or config.DEFAULT_LOCATION
    
    # Calculate timing breakdowns for interview agenda
    technical_duration = int(duration * 0.4)  # 40% for technical
    experience_duration = int(duration * 0.3)  # 30% for experience
    culture_duration = int(duration * 0.2)    # 20% for culture
    qa_duration = duration - (technical_duration + experience_duration + culture_duration)
    
    # Format datetime
    interview_date_str = interview_datetime.strftime("%A, %B %d, %Y at %I:%M %p %Z")
    response_deadline = (interview_datetime - timedelta(days=1)).strftime("%A, %B %d")
    
    # Prepare template variables
    template_vars = {
        "candidate_name": candidate_name,
        "jd_title": jd_title,
        "company_name": config.COMPANY_NAME,
        "company_website": config.COMPANY_WEBSITE,
        "interview_date": interview_date_str,
        "duration": duration,
        "location": location,
        "meeting_link": kwargs.get("meeting_link", "Will be provided separately"),
        "response_deadline": response_deadline,
        "interviewer_name": kwargs.get("interviewer_name", "Hiring Team"),
        "contact_email": config.EMAIL_FROM,
        "contact_phone": kwargs.get("contact_phone", "Available upon request"),
        "backup_contact": kwargs.get("backup_contact", config.EMAIL_FROM),
        "technical_duration": technical_duration,
        "experience_duration": experience_duration,
        "culture_duration": culture_duration,
        "qa_duration": qa_duration,
        "key_skills": kwargs.get("key_skills", "relevant technologies"),
        "candidate_strengths": kwargs.get("candidate_strengths", "your technical background"),
        "discussed_topics": kwargs.get("discussed_topics", "your experience and projects"),
        "positive_highlights": kwargs.get("positive_highlights", "your technical expertise"),
        "decision_deadline": kwargs.get("decision_deadline", "end of next week"),
        "communication_deadline": kwargs.get("communication_deadline", "within 5 business days")
    }
    
    # Update with any additional kwargs
    template_vars.update(kwargs)
    
    try:
        formatted_subject = template["subject"].format(**template_vars)
        formatted_body = template["body"].format(**template_vars)
        
        return {
            "subject": formatted_subject,
            "body": formatted_body
        }
    except KeyError as e:
        # Fallback to basic template if formatting fails
        return {
            "subject": f"Interview Invitation - {jd_title}",
            "body": f"Dear {candidate_name},\\n\\nThank you for your interest in the {jd_title} position. We would like to schedule an interview.\\n\\nBest regards,\\n{config.COMPANY_NAME} Team"
        }

def generate_rejection_email(
    candidate_name: str,
    jd_title: str,
    candidate_skills: list = None,
    **kwargs
) -> Dict[str, str]:
    """Generate a polite rejection email."""
    # Identify candidate strengths from their skills
    if candidate_skills:
        strengths = ", ".join(candidate_skills[:3])  # Mention top 3 skills
    else:
        strengths = "your technical background"
    
    return format_interview_email(
        candidate_name=candidate_name,
        candidate_email="",  # Not needed for rejection
        jd_title=jd_title,
        interview_datetime=datetime.now(),  # Not used for rejection
        template_type="rejection_polite",
        candidate_strengths=strengths,
        **kwargs
    )
