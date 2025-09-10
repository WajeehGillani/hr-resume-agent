"""
Internal MCP tool for HR Interview Orchestrator.
Implements parse_job_description for internal use only.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from src.tools.parser import parse_jd_to_struct
from src.state import JD

class MCPJobDescriptionTool:
    """Internal MCP tool for job description parsing."""
    
    def __init__(self):
        self.tool_name = "parse_job_description"
        self.description = "Extract structured requirements from job descriptions"
        
    def get_tool_schema(self) -> Dict[str, Any]:
        """Get the MCP tool schema definition."""
        return {
            "name": self.tool_name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "job_description": {
                        "type": "string",
                        "description": "Raw job description text"
                    },
                    "format": {
                        "type": "string", 
                        "enum": ["auto", "pdf", "docx", "md", "txt"],
                        "default": "auto",
                        "description": "Input format hint (auto-detected if not specified)"
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include parsing metadata in response"
                    }
                },
                "required": ["job_description"]
            }
        }
    
    def parse_job_description(
        self, 
        job_description: str, 
        format: str = "auto",
        include_metadata: bool = True
    ) -> str:
        """
        Parse a job description to extract structured requirements.
        
        Args:
            job_description: Raw job description text
            format: Input format hint (auto, pdf, docx, md, txt)
            include_metadata: Include parsing metadata in response
            
        Returns:
            JSON string with extracted title, location, must_haves, nice_haves
        """
        try:
            # Use the existing parser
            jd: JD = parse_jd_to_struct(job_description)
            
            # Build structured response
            result = {
                "title": jd.title,
                "location": jd.location,
                "must_haves": jd.must_haves,
                "nice_haves": jd.nice_haves,
                "parsing_status": "success"
            }
            
            if include_metadata:
                result["metadata"] = {
                    "parsed_at": datetime.now().isoformat(),
                    "input_format": format,
                    "input_length": len(job_description),
                    "requirements_count": len(jd.must_haves),
                    "preferred_count": len(jd.nice_haves),
                    "has_location": bool(jd.location),
                    "parsing_method": "openai" if job_description else "offline"
                }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            error_result = {
                "parsing_status": "error",
                "error": str(e),
                "title": "Unknown",
                "location": None,
                "must_haves": [],
                "nice_haves": []
            }
            
            if include_metadata:
                error_result["metadata"] = {
                    "parsed_at": datetime.now().isoformat(),
                    "input_format": format,
                    "input_length": len(job_description) if job_description else 0,
                    "error_type": type(e).__name__
                }
            
            return json.dumps(error_result, indent=2)
    
    def parse_from_file(self, file_path: str, include_metadata: bool = True) -> str:
        """
        Parse job description from a file.
        
        Args:
            file_path: Path to job description file
            include_metadata: Include parsing metadata in response
            
        Returns:
            JSON string with parsing results
        """
        try:
            from src.tools.parser import load_text
            
            # Load text from file
            job_text = load_text(file_path)
            
            # Determine format from file extension
            file_ext = Path(file_path).suffix.lower()
            format_map = {
                '.pdf': 'pdf',
                '.docx': 'docx', 
                '.doc': 'docx',
                '.md': 'md',
                '.txt': 'txt'
            }
            format_hint = format_map.get(file_ext, 'auto')
            
            return self.parse_job_description(
                job_text, 
                format=format_hint, 
                include_metadata=include_metadata
            )
            
        except Exception as e:
            error_result = {
                "parsing_status": "file_error",
                "error": f"Could not load file: {str(e)}",
                "file_path": file_path,
                "title": "Unknown",
                "location": None,
                "must_haves": [],
                "nice_haves": []
            }
            
            if include_metadata:
                error_result["metadata"] = {
                    "parsed_at": datetime.now().isoformat(),
                    "input_file": file_path,
                    "error_type": type(e).__name__
                }
            
            return json.dumps(error_result, indent=2)
    
    def validate_job_description(self, job_description: str) -> Dict[str, Any]:
        """
        Validate job description quality and completeness.
        
        Args:
            job_description: Raw job description text
            
        Returns:
            Validation results with quality score and suggestions
        """
        try:
            # Parse the JD first
            jd: JD = parse_jd_to_struct(job_description)
            
            # Quality checks
            quality_score = 0.0
            issues = []
            suggestions = []
            
            # Check title (20 points)
            if jd.title and jd.title != "Unknown Position":
                quality_score += 20
            else:
                issues.append("Missing or unclear job title")
                suggestions.append("Add a clear, specific job title")
            
            # Check location (10 points)
            if jd.location:
                quality_score += 10
            else:
                issues.append("Missing location information")
                suggestions.append("Specify work location (remote/hybrid/on-site)")
            
            # Check must-have requirements (40 points)
            if len(jd.must_haves) >= 3:
                quality_score += 40
            elif len(jd.must_haves) >= 1:
                quality_score += 20
                suggestions.append("Add more specific required skills (aim for 3-5)")
            else:
                issues.append("No clear required skills identified")
                suggestions.append("Add specific required skills and qualifications")
            
            # Check nice-to-have requirements (15 points)
            if len(jd.nice_haves) >= 2:
                quality_score += 15
            elif len(jd.nice_haves) >= 1:
                quality_score += 8
            else:
                suggestions.append("Consider adding preferred/nice-to-have skills")
            
            # Check content length and detail (15 points)
            if len(job_description) >= 500:
                quality_score += 15
            elif len(job_description) >= 200:
                quality_score += 8
            else:
                issues.append("Job description seems too brief")
                suggestions.append("Add more details about role, responsibilities, and requirements")
            
            # Determine quality tier
            if quality_score >= 80:
                quality_tier = "Excellent"
            elif quality_score >= 60:
                quality_tier = "Good"
            elif quality_score >= 40:
                quality_tier = "Fair"
            else:
                quality_tier = "Needs Improvement"
            
            return {
                "quality_score": quality_score,
                "quality_tier": quality_tier,
                "issues": issues,
                "suggestions": suggestions,
                "requirements_found": len(jd.must_haves),
                "preferences_found": len(jd.nice_haves),
                "has_title": bool(jd.title and jd.title != "Unknown Position"),
                "has_location": bool(jd.location)
            }
            
        except Exception as e:
            return {
                "quality_score": 0,
                "quality_tier": "Error",
                "issues": [f"Parsing failed: {str(e)}"],
                "suggestions": ["Fix formatting and try again"],
                "error": str(e)
            }

# Global instance for internal use
job_description_tool = MCPJobDescriptionTool()

# Convenience functions for direct use
def parse_job_description_internal(job_description: str, include_metadata: bool = True) -> Dict[str, Any]:
    """
    Internal function to parse job description and return Python dict.
    
    Args:
        job_description: Raw job description text
        include_metadata: Include parsing metadata
        
    Returns:
        Parsed job description as Python dictionary
    """
    result_json = job_description_tool.parse_job_description(
        job_description, include_metadata=include_metadata
    )
    return json.loads(result_json)

def validate_job_description_quality(job_description: str) -> Dict[str, Any]:
    """
    Internal function to validate job description quality.
    
    Args:
        job_description: Raw job description text
        
    Returns:
        Quality validation results
    """
    return job_description_tool.validate_job_description(job_description)
