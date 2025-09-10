"""
Rich console output and human-readable displays for HR Interview Orchestrator.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from typing import List, Dict, Any
import time

from src.state import OrchestratorState, Candidate, JD
from src.config import config

console = Console()

class HRDisplay:
    """Rich console display manager for HR Interview Orchestrator."""
    
    def __init__(self):
        self.console = Console()
        self.progress = None
        self.current_task = None
    
    def show_header(self):
        """Display application header."""
        header_text = Text("HR Interview Orchestrator", style="bold blue")
        header_text.append(" 🎯", style="bold yellow")
        
        header_panel = Panel(
            header_text,
            subtitle=f"Developed by {config.COMPANY_NAME}",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(header_panel)
        self.console.print("")
    
    def show_config_status(self):
        """Display configuration status and warnings."""
        issues = config.validate_required_config()
        
        if issues:
            self.console.print("⚙️  [bold yellow]Configuration Status:[/bold yellow]")
            for issue in issues:
                self.console.print(f"  {issue}")
            self.console.print("")
    
    def show_job_summary(self, jd: JD):
        """Display job description summary."""
        # Job title and basic info
        title_text = Text(jd.title, style="bold green")
        location_text = Text(f"📍 {jd.location or 'Remote/Not specified'}", style="dim")
        
        # Must-have skills in a nice format
        skills_text = Text()
        for i, skill in enumerate(jd.must_haves[:6]):  # Show max 6 to avoid clutter
            if i > 0:
                skills_text.append(" • ", style="dim")
            skills_text.append(skill, style="cyan")
        
        if len(jd.must_haves) > 6:
            skills_text.append(f" • +{len(jd.must_haves) - 6} more", style="dim")
        
        job_content = f"{title_text}\n{location_text}\n\n🔧 Required Skills:\n{skills_text}"
        
        job_panel = Panel(
            job_content,
            title="📄 Job Description",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(job_panel)
    
    def start_progress(self, total_steps: int = 100) -> Progress:
        """Start progress tracking."""
        self.progress = Progress(console=self.console)
        self.progress.start()
        self.current_task = self.progress.add_task("🚀 Starting...", total=total_steps)
        return self.progress
    
    def update_progress(self, description: str, advance: int = 0):
        """Update progress with new description."""
        if self.progress and self.current_task is not None:
            self.progress.update(self.current_task, description=description, advance=advance)
    
    def finish_progress(self):
        """Complete and stop progress tracking."""
        if self.progress:
            self.progress.update(self.current_task, description="✅ Complete!", completed=100)
            time.sleep(0.5)  # Brief pause to show completion
            self.progress.stop()
    
    def show_candidate_rankings(self, candidates: List[Candidate], scheduled_count: int = 2):
        """Display candidate rankings in a beautiful table."""
        if not candidates:
            self.console.print("❌ No candidates found or shortlisted.")
            return
        
        table = Table(title="🏆 Candidate Rankings")
        table.add_column("Rank", style="cyan", width=6, justify="center")
        table.add_column("Name", style="magenta", width=25)
        table.add_column("Score", style="green", width=8, justify="right")
        table.add_column("Match %", style="yellow", width=10, justify="right")
        table.add_column("Experience", style="blue", width=12, justify="center")
        table.add_column("Email Status", style="white", width=15)
        table.add_column("Status", style="bold", width=12)
        
        for i, candidate in enumerate(candidates, 1):
            # Calculate match percentage
            match_pct = f"{candidate.score * 100:.1f}%"
            
            # Experience formatting
            exp_text = f"{candidate.years_exp}y" if candidate.years_exp > 0 else "N/A"
            
            # Email status
            email_status = "✅ Found" if candidate.email else "❌ Missing"
            
            # Interview status
            if i <= scheduled_count:
                status = "📅 Scheduled"
                status_style = "green"
            else:
                status = "⏸️  Waitlist"
                status_style = "yellow"
            
            # Color code score
            if candidate.score >= 0.7:
                score_style = "bold green"
            elif candidate.score >= 0.4:
                score_style = "yellow"
            else:
                score_style = "red"
            
            table.add_row(
                f"#{i}",
                candidate.name,
                f"[{score_style}]{candidate.score:.3f}[/{score_style}]",
                match_pct,
                exp_text,
                email_status,
                f"[{status_style}]{status}[/{status_style}]"
            )
        
        self.console.print(table)
        self.console.print("")
    
    def show_questions_preview(self, questions: List[str], max_show: int = 5):
        """Display a preview of generated interview questions."""
        if not questions:
            return
        
        questions_text = Text()
        for i, question in enumerate(questions[:max_show], 1):
            questions_text.append(f"{i}. ", style="cyan")
            questions_text.append(f"{question}\n\n", style="white")
        
        if len(questions) > max_show:
            questions_text.append(f"... and {len(questions) - max_show} more questions", style="dim")
        
        questions_panel = Panel(
            questions_text,
            title=f"❓ Interview Questions ({len(questions)} total)",
            border_style="yellow",
            padding=(1, 2)
        )
        self.console.print(questions_panel)
    
    def show_artifacts_summary(self, artifacts: Dict[str, Any], metrics: Dict[str, Any]):
        """Display summary of generated artifacts and metrics."""
        # Artifacts summary
        emails_count = len(artifacts.get("emails", []))
        invites_count = len(artifacts.get("invites", []))
        gmail_drafts = len(artifacts.get("gmail_drafts", []))
        
        artifacts_text = Text()
        artifacts_text.append(f"📧 Email Drafts: {emails_count}\n", style="green")
        artifacts_text.append(f"📅 Calendar Invites: {invites_count}\n", style="blue")
        if gmail_drafts > 0:
            artifacts_text.append(f"✉️  Gmail Drafts: {gmail_drafts}\n", style="magenta")
        
        # Metrics
        elapsed = metrics.get("elapsed_seconds", 0)
        candidates_processed = metrics.get("num_candidates", 0)
        questions_generated = metrics.get("num_questions", 0)
        
        metrics_text = Text()
        metrics_text.append(f"⏱️  Processing Time: {elapsed:.1f}s\n", style="cyan")
        metrics_text.append(f"👥 Candidates Processed: {candidates_processed}\n", style="white")
        metrics_text.append(f"❓ Questions Generated: {questions_generated}\n", style="yellow")
        
        if metrics.get("needed_widening"):
            metrics_text.append("🔍 Search Widened (low matches)\n", style="orange1")
        
        # Combined panel
        summary_layout = Layout()
        summary_layout.split_row(
            Layout(Panel(artifacts_text, title="📦 Artifacts", border_style="green"), name="artifacts"),
            Layout(Panel(metrics_text, title="📊 Metrics", border_style="blue"), name="metrics")
        )
        
        self.console.print(summary_layout)
    
    def show_next_steps(self, artifacts: Dict[str, Any]):
        """Display recommended next steps for the user."""
        steps = []
        
        # Check artifacts location
        if artifacts.get("emails"):
            steps.append("📧 Review and send email drafts from artifacts/ folder")
        
        if artifacts.get("invites"):
            steps.append("📅 Import calendar invites (.ics files) to your calendar")
        
        if artifacts.get("gmail_drafts"):
            steps.append("✉️  Check Gmail drafts (already created in your account)")
        
        steps.append("📋 Review candidate scores and interview questions")
        steps.append("🤝 Prepare interview materials and meeting rooms")
        
        if steps:
            steps_text = Text()
            for i, step in enumerate(steps, 1):
                steps_text.append(f"{i}. {step}\n", style="white")
            
            next_steps_panel = Panel(
                steps_text,
                title="🎯 Next Steps",
                border_style="cyan",
                padding=(1, 2)
            )
            self.console.print(next_steps_panel)
    
    def show_error(self, message: str, details: str = None):
        """Display error message."""
        error_text = Text(message, style="bold red")
        if details:
            error_text.append(f"\n\nDetails: {details}", style="red")
        
        error_panel = Panel(
            error_text,
            title="❌ Error",
            border_style="red",
            padding=(1, 2)
        )
        self.console.print(error_panel)
    
    def show_warning(self, message: str):
        """Display warning message."""
        warning_panel = Panel(
            Text(message, style="yellow"),
            title="⚠️  Warning",
            border_style="yellow",
            padding=(1, 2)
        )
        self.console.print(warning_panel)

# Global display instance
display = HRDisplay()
