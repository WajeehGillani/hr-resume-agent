"""
File management and organization for HR Interview Orchestrator artifacts.
Provides structured storage, cleanup utilities, and organized output.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

from src.config import config

class ArtifactsManager:
    """Manages organized storage and cleanup of generated artifacts."""
    
    def __init__(self, job_title: str = None, run_id: str = None, create_dirs: bool = True):
        self.base_dir = config.ARTIFACTS_DIR
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.job_title = self._sanitize_filename(job_title or "interview")
        
        # Create organized structure
        self.current_run_dir = self.base_dir / "runs" / f"{self.run_id}_{self.job_title}"
        self.emails_dir = self.current_run_dir / "emails"
        self.calendars_dir = self.current_run_dir / "calendars"
        self.reports_dir = self.current_run_dir / "reports"
        self.logs_dir = self.current_run_dir / "logs"
        
        # Cache and persistent data
        self.cache_dir = self.base_dir / "cache"
        self.templates_dir = self.base_dir / "templates"
        
        # Only create directories if explicitly requested (for actual runs)
        if create_dirs:
            self._setup_directories()
    
    def _sanitize_filename(self, name: str) -> str:
        """Convert job title to safe filename."""
        if not name:
            return "interview"
        # Remove unsafe characters and limit length
        safe = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe = safe.replace(' ', '_').lower()
        return safe[:30]  # Limit length
    
    def _setup_directories(self):
        """Create organized directory structure."""
        directories = [
            self.current_run_dir,
            self.emails_dir,
            self.calendars_dir,
            self.reports_dir,
            self.logs_dir,
            self.cache_dir,
            self.templates_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def ensure_base_directories(self):
        """Ensure only base directories exist (for cleanup operations)."""
        base_directories = [
            self.cache_dir,
            self.templates_dir,
            self.base_dir / "runs"
        ]
        
        for directory in base_directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_email_path(self, candidate_name: str, index: int) -> str:
        """Get organized path for email file."""
        safe_name = self._sanitize_filename(candidate_name)
        filename = f"{index:02d}_{safe_name}.eml"
        return str(self.emails_dir / filename)
    
    def get_calendar_path(self, candidate_name: str, index: int) -> str:
        """Get organized path for calendar file."""
        safe_name = self._sanitize_filename(candidate_name)
        filename = f"{index:02d}_{safe_name}.ics"
        return str(self.calendars_dir / filename)
    
    def get_report_path(self, report_type: str = "summary") -> str:
        """Get organized path for reports."""
        if report_type == "html":
            filename = "interview_report.html"
        elif report_type == "json":
            filename = "results.json"
        else:
            filename = f"{report_type}_report.json"
        return str(self.reports_dir / filename)
    
    def get_log_path(self, log_type: str = "execution") -> str:
        """Get organized path for logs."""
        filename = f"{log_type}_{self.run_id}.jsonl"
        return str(self.logs_dir / filename)
    
    def save_run_summary(self, summary_data: Dict) -> str:
        """Save a run summary with metadata."""
        summary_data.update({
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "job_title": self.job_title,
            "artifacts_location": str(self.current_run_dir)
        })
        
        summary_path = self.current_run_dir / "run_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2)
        
        return str(summary_path)
    
    def create_quick_access_links(self):
        """Create symlinks/shortcuts for latest run."""
        latest_dir = self.base_dir / "latest"
        
        # Remove existing latest directory
        if latest_dir.exists():
            if latest_dir.is_symlink():
                latest_dir.unlink()
            else:
                shutil.rmtree(latest_dir)
        
        # Create new symlink to current run
        try:
            latest_dir.symlink_to(self.current_run_dir, target_is_directory=True)
        except OSError:
            # Fallback: copy instead of symlink on Windows without admin rights
            shutil.copytree(self.current_run_dir, latest_dir)
    
    def move_cache_files(self):
        """Move persistent cache files to organized cache directory."""
        cache_files = [
            ("qbank.npy", "embeddings_cache.npy"),
            ("qbank_meta.json", "embeddings_meta.json"),
        ]
        
        for old_file, new_file in cache_files:
            old_path = self.base_dir / old_file
            new_path = self.cache_dir / new_file
            
            if old_path.exists() and not new_path.exists():
                shutil.move(str(old_path), str(new_path))
        
        # Move FAISS cache
        old_faiss = self.base_dir / "faiss_qbank"
        new_faiss = self.cache_dir / "faiss_qbank"
        
        if old_faiss.exists() and not new_faiss.exists():
            shutil.move(str(old_faiss), str(new_faiss))
    
    def cleanup_old_runs(self, keep_latest: int = 10):
        """Clean up old run directories, keeping only the latest N runs."""
        runs_dir = self.base_dir / "runs"
        if not runs_dir.exists():
            return
        
        # Get all run directories sorted by modification time
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        run_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Remove old runs beyond the keep_latest limit
        for old_run in run_dirs[keep_latest:]:
            try:
                shutil.rmtree(old_run)
                print(f"Cleaned up old run: {old_run.name}")
            except Exception as e:
                print(f"Warning: Could not remove {old_run.name}: {e}")
    
    def cleanup_legacy_files(self):
        """Clean up legacy files from root artifacts directory."""
        legacy_patterns = [
            "email_candidate*.eml",
            "invite*.ics", 
            "output.json",
            "run_*.jsonl",
            "interview_report.html"
        ]
        
        import glob
        for pattern in legacy_patterns:
            for file_path in glob.glob(str(self.base_dir / pattern)):
                try:
                    os.remove(file_path)
                    print(f"Cleaned up legacy file: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"Warning: Could not remove {file_path}: {e}")
    
    def fix_duplicate_structures(self):
        """Fix duplicate directory structures in artifacts."""
        print("🔧 Fixing duplicate directory structures...")
        
        # Fix artifacts/artifacts duplication
        duplicate_artifacts = self.base_dir / "artifacts"
        if duplicate_artifacts.exists():
            # Move contents up one level
            for item in duplicate_artifacts.iterdir():
                target = self.base_dir / item.name
                if not target.exists():
                    try:
                        shutil.move(str(item), str(target))
                        print(f"Moved {item.name} from duplicate artifacts/")
                    except Exception as e:
                        print(f"Warning: Could not move {item.name}: {e}")
            
            # Remove empty duplicate directory
            try:
                shutil.rmtree(duplicate_artifacts)
                print("Removed duplicate artifacts/ directory")
            except Exception as e:
                print(f"Warning: Could not remove duplicate artifacts/: {e}")
        
        # Fix duplicate faiss_qbank (keep the one in cache)
        root_faiss = self.base_dir / "faiss_qbank"
        cache_faiss = self.cache_dir / "faiss_qbank"
        
        if root_faiss.exists() and cache_faiss.exists():
            # Compare timestamps to keep the newer one
            root_time = root_faiss.stat().st_mtime
            cache_time = cache_faiss.stat().st_mtime
            
            if root_time > cache_time:
                # Root is newer, move it to cache
                try:
                    shutil.rmtree(cache_faiss)
                    shutil.move(str(root_faiss), str(cache_faiss))
                    print("Updated faiss_qbank in cache with newer version")
                except Exception as e:
                    print(f"Warning: Could not update faiss_qbank: {e}")
            else:
                # Cache is newer or same, remove root duplicate
                try:
                    shutil.rmtree(root_faiss)
                    print("Removed duplicate faiss_qbank from root")
                except Exception as e:
                    print(f"Warning: Could not remove root faiss_qbank: {e}")
        
        # Remove empty runs directories
        for runs_dir in [self.base_dir / "runs"]:
            if runs_dir.exists() and not any(runs_dir.iterdir()):
                try:
                    runs_dir.rmdir()
                    print(f"Removed empty directory: {runs_dir.name}")
                except Exception as e:
                    print(f"Warning: Could not remove empty {runs_dir.name}: {e}")
    
    def generate_artifacts_index(self) -> str:
        """Generate an index of all runs and artifacts."""
        runs_dir = self.base_dir / "runs"
        index_data = {
            "generated_at": datetime.now().isoformat(),
            "total_runs": 0,
            "runs": []
        }
        
        if runs_dir.exists():
            run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], 
                            key=lambda x: x.stat().st_mtime, reverse=True)
            
            index_data["total_runs"] = len(run_dirs)
            
            for run_dir in run_dirs:
                run_summary_path = run_dir / "run_summary.json"
                if run_summary_path.exists():
                    try:
                        with open(run_summary_path, 'r', encoding='utf-8') as f:
                            run_summary = json.load(f)
                        index_data["runs"].append({
                            "run_id": run_summary.get("run_id", run_dir.name),
                            "job_title": run_summary.get("job_title", "Unknown"),
                            "timestamp": run_summary.get("timestamp", "Unknown"),
                            "path": str(run_dir),
                            "candidates_processed": run_summary.get("process_summary", {}).get("total_candidates_processed", 0),
                            "interviews_scheduled": run_summary.get("process_summary", {}).get("interviews_scheduled", 0)
                        })
                    except Exception:
                        # Fallback for runs without summary
                        index_data["runs"].append({
                            "run_id": run_dir.name,
                            "job_title": "Unknown",
                            "timestamp": datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat(),
                            "path": str(run_dir),
                            "candidates_processed": "Unknown",
                            "interviews_scheduled": "Unknown"
                        })
        
        index_path = self.base_dir / "runs_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        
        return str(index_path)

class CleanupUtility:
    """Utility for cleaning up and organizing artifacts."""
    
    @staticmethod
    def full_cleanup(keep_runs: int = 10, keep_cache: bool = True):
        """Perform comprehensive cleanup of artifacts directory."""
        print("🧹 Starting artifacts cleanup...")
        
        # Create manager without creating new run directories
        manager = ArtifactsManager(create_dirs=False)
        
        # Ensure base directories exist for cleanup operations
        manager.ensure_base_directories()
        
        # Fix duplicate structures first
        manager.fix_duplicate_structures()
        
        # Move cache files to organized location
        if keep_cache:
            print("📦 Organizing cache files...")
            manager.move_cache_files()
        
        # Clean up legacy files
        print("🗑️  Removing legacy files...")
        manager.cleanup_legacy_files()
        
        # Clean up old runs
        print(f"📚 Keeping latest {keep_runs} runs...")
        manager.cleanup_old_runs(keep_runs)
        
        # Generate index
        print("📝 Generating artifacts index...")
        index_path = manager.generate_artifacts_index()
        
        print(f"✅ Cleanup complete! Index created at: {index_path}")
    
    @staticmethod
    def list_runs(limit: int = 20):
        """List recent runs with summary information."""
        runs_dir = config.ARTIFACTS_DIR / "runs"
        if not runs_dir.exists():
            print("No runs found.")
            return
        
        run_dirs = sorted([d for d in runs_dir.iterdir() if d.is_dir()], 
                         key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not run_dirs:
            print("📋 No runs found in artifacts/runs/")
            return
            
        print(f"📋 Recent runs (showing {min(limit, len(run_dirs))}):")
        print("-" * 80)
        
        for i, run_dir in enumerate(run_dirs[:limit], 1):
            run_summary_path = run_dir / "run_summary.json"
            if run_summary_path.exists():
                try:
                    with open(run_summary_path, 'r', encoding='utf-8') as f:
                        summary = json.load(f)
                    
                    timestamp = summary.get("timestamp", "Unknown")
                    job_title = summary.get("job_title", "Unknown")
                    candidates = summary.get("process_summary", {}).get("total_candidates_processed", "?")
                    scheduled = summary.get("process_summary", {}).get("interviews_scheduled", "?")
                    
                    print(f"{i:2d}. {job_title} | {timestamp[:19]} | {candidates} candidates | {scheduled} scheduled")
                    print(f"    📁 {run_dir}")
                except Exception:
                    mod_time = datetime.fromtimestamp(run_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    print(f"{i:2d}. {run_dir.name} | {mod_time} | No summary")
                    print(f"    📁 {run_dir}")
            else:
                mod_time = datetime.fromtimestamp(run_dir.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                print(f"{i:2d}. {run_dir.name} | {mod_time} | No summary")
                print(f"    📁 {run_dir}")
        
        if len(run_dirs) > limit:
            print(f"... and {len(run_dirs) - limit} more runs")

def get_artifacts_manager(job_title: str = None) -> ArtifactsManager:
    """Factory function to get artifacts manager for current run."""
    return ArtifactsManager(job_title=job_title)
