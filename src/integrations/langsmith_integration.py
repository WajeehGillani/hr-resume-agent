"""
LangSmith integration for comprehensive tracing and evaluation of the HR Interview Orchestrator.
Provides detailed observability into LLM calls, agent decisions, and overall pipeline performance.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import uuid

from src.config import config

try:
    from langsmith import Client, traceable
    from langsmith.schemas import Run, Example, Dataset
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    # Fallback decorators when LangSmith is not available
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if args else decorator

class LangSmithTracer:
    """LangSmith integration for HR Interview Orchestrator tracing."""
    
    def __init__(self):
        self.client = None
        self.enabled = config.LANGSMITH_TRACING and LANGSMITH_AVAILABLE
        self.project_name = config.LANGSMITH_PROJECT
        self.session_id = str(uuid.uuid4())
        
        if self.enabled:
            try:
                # Configure LangSmith environment
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_PROJECT"] = self.project_name
                
                if config.LANGSMITH_API_KEY:
                    os.environ["LANGCHAIN_API_KEY"] = config.LANGSMITH_API_KEY
                
                self.client = Client()
                self._initialize_project()
            except Exception as e:
                print(f"⚠️  LangSmith initialization failed: {e}")
                self.enabled = False
    
    def _initialize_project(self):
        """Initialize or ensure LangSmith project exists."""
        try:
            # Try to get existing project
            self.client.read_project(project_name=self.project_name)
        except Exception:
            # Create project if it doesn't exist
            try:
                self.client.create_project(
                    project_name=self.project_name,
                    description="HR Interview Orchestrator - AI-powered candidate screening and interview automation"
                )
            except Exception as e:
                print(f"Warning: Could not create LangSmith project: {e}")
    
    @traceable(name="hr_orchestrator_full_run")
    def trace_full_run(self, jd_title: str, candidates_count: int, processing_func: Callable) -> Any:
        """Trace the entire HR orchestrator pipeline execution."""
        if not self.enabled:
            return processing_func()
        
        with self.client.trace(
            name=f"HR Pipeline: {jd_title}",
            session_id=self.session_id,
            metadata={
                "job_title": jd_title,
                "candidates_count": candidates_count,
                "timestamp": datetime.now().isoformat(),
                "version": "2.0"
            }
        ) as run_context:
            try:
                result = processing_func()
                
                # Log successful completion
                run_context.end(
                    outputs={
                        "status": "success",
                        "shortlisted_count": len(getattr(result, 'shortlisted', [])),
                        "questions_count": len(getattr(result, 'questions', [])),
                        "schema_valid": getattr(result, 'schema_ok', False)
                    }
                )
                
                return result
            except Exception as e:
                run_context.end(
                    outputs={"status": "error", "error": str(e)}
                )
                raise
    
    @traceable(name="jd_parsing")
    def trace_jd_parsing(self, jd_text: str, parsing_func: Callable) -> Any:
        """Trace job description parsing process."""
        if not self.enabled:
            return parsing_func()
        
        return self._trace_component(
            name="Job Description Parsing",
            inputs={"jd_length": len(jd_text), "has_openai_key": bool(config.OPENAI_API_KEY)},
            processing_func=parsing_func
        )
    
    @traceable(name="candidate_scoring")
    def trace_candidate_scoring(self, candidate_name: str, jd_requirements: List[str], scoring_func: Callable) -> Any:
        """Trace individual candidate scoring process."""
        if not self.enabled:
            return scoring_func()
        
        return self._trace_component(
            name=f"Candidate Scoring: {candidate_name}",
            inputs={
                "candidate": candidate_name,
                "requirements_count": len(jd_requirements),
                "requirements": jd_requirements[:5]  # First 5 for tracing
            },
            processing_func=scoring_func
        )
    
    @traceable(name="question_generation")
    def trace_question_generation(self, jd_title: str, skills: List[str], generation_func: Callable) -> Any:
        """Trace interview question generation process."""
        if not self.enabled:
            return generation_func()
        
        return self._trace_component(
            name=f"Question Generation: {jd_title}",
            inputs={
                "job_title": jd_title,
                "skills_count": len(skills),
                "key_skills": skills[:10]  # First 10 for tracing
            },
            processing_func=generation_func
        )
    
    def _trace_component(self, name: str, inputs: Dict[str, Any], processing_func: Callable) -> Any:
        """Generic component tracing wrapper."""
        try:
            result = processing_func()
            
            # Extract meaningful outputs based on result type
            outputs = self._extract_outputs(result)
            
            # Log to LangSmith
            if self.client:
                self.client.create_run(
                    name=name,
                    inputs=inputs,
                    outputs=outputs,
                    session_id=self.session_id,
                    run_type="chain"
                )
            
            return result
        except Exception as e:
            # Log error
            if self.client:
                self.client.create_run(
                    name=name,
                    inputs=inputs,
                    outputs={"error": str(e)},
                    session_id=self.session_id,
                    run_type="chain"
                )
            raise
    
    def _extract_outputs(self, result: Any) -> Dict[str, Any]:
        """Extract meaningful outputs from processing results."""
        if hasattr(result, '__dict__'):
            # Pydantic model or similar
            outputs = {}
            for key, value in result.__dict__.items():
                if key.startswith('_'):
                    continue
                if isinstance(value, (str, int, float, bool, list)):
                    if isinstance(value, list) and len(value) > 10:
                        outputs[f"{key}_count"] = len(value)
                        outputs[f"{key}_sample"] = value[:3]
                    else:
                        outputs[key] = value
            return outputs
        elif isinstance(result, dict):
            return result
        elif isinstance(result, (list, tuple)):
            return {"result_count": len(result), "sample": result[:3] if result else []}
        else:
            return {"result_type": type(result).__name__}
    
    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics to LangSmith."""
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.create_run(
                name="Performance Metrics",
                inputs={"timestamp": datetime.now().isoformat()},
                outputs=metrics,
                session_id=self.session_id,
                run_type="chain"
            )
        except Exception as e:
            print(f"Warning: Could not log performance metrics: {e}")
    
    def create_dataset_from_run(self, run_data: Dict[str, Any]):
        """Create evaluation dataset from successful run."""
        if not self.enabled or not self.client:
            return
        
        try:
            dataset_name = f"hr-orchestrator-{datetime.now().strftime('%Y%m')}"
            
            # Create dataset if it doesn't exist
            try:
                dataset = self.client.read_dataset(dataset_name=dataset_name)
            except:
                dataset = self.client.create_dataset(
                    dataset_name=dataset_name,
                    description="HR Interview Orchestrator evaluation dataset"
                )
            
            # Add successful run as example
            example_data = {
                "inputs": {
                    "job_title": run_data.get("job_description", {}).get("title"),
                    "required_skills": run_data.get("job_description", {}).get("required_skills", []),
                    "candidates_count": run_data.get("process_summary", {}).get("total_candidates_processed", 0)
                },
                "outputs": {
                    "shortlisted_count": run_data.get("process_summary", {}).get("candidates_shortlisted", 0),
                    "questions_generated": run_data.get("process_summary", {}).get("questions_generated", 0),
                    "processing_time": run_data.get("process_summary", {}).get("processing_time_seconds", 0)
                }
            }
            
            self.client.create_example(
                dataset_id=dataset.id,
                inputs=example_data["inputs"],
                outputs=example_data["outputs"]
            )
            
        except Exception as e:
            print(f"Warning: Could not create dataset example: {e}")
    
    def get_run_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get run statistics from LangSmith for the last N days."""
        if not self.enabled or not self.client:
            return {}
        
        try:
            runs = self.client.list_runs(
                project_name=self.project_name,
                limit=100
            )
            
            stats = {
                "total_runs": len(list(runs)),
                "success_rate": 0,
                "avg_processing_time": 0,
                "common_errors": []
            }
            
            return stats
        except Exception as e:
            print(f"Warning: Could not get run statistics: {e}")
            return {}

# Global tracer instance
tracer = LangSmithTracer()

# Convenience functions
def trace_jd_parsing(func):
    """Decorator for tracing JD parsing functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > 0 and isinstance(args[0], str):
            return tracer.trace_jd_parsing(args[0], lambda: func(*args, **kwargs))
        return func(*args, **kwargs)
    return wrapper

def trace_candidate_scoring(func):
    """Decorator for tracing candidate scoring functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract candidate name and requirements if available
        candidate_name = "Unknown"
        requirements = []
        
        if len(args) >= 2:
            # Assume first arg is JD, second is candidate
            if hasattr(args[1], 'name'):
                candidate_name = args[1].name
            if hasattr(args[0], 'must_haves'):
                requirements = args[0].must_haves
        
        return tracer.trace_candidate_scoring(
            candidate_name, requirements, lambda: func(*args, **kwargs)
        )
    return wrapper

def trace_question_generation(func):
    """Decorator for tracing question generation functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        jd_title = "Unknown"
        skills = []
        
        if len(args) > 0 and hasattr(args[0], 'jd'):
            if hasattr(args[0].jd, 'title'):
                jd_title = args[0].jd.title
            if hasattr(args[0].jd, 'must_haves'):
                skills = args[0].jd.must_haves
        
        return tracer.trace_question_generation(
            jd_title, skills, lambda: func(*args, **kwargs)
        )
    return wrapper
