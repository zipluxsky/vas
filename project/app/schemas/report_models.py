from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class ReportGenerationRequest(BaseModel):
    target_date: Optional[str] = None
    report_type: str = "file_confirmation"
    formats: List[str] = ["csv", "xlsx"]

class FileConfirmationInput(BaseModel):
    """Input for File Confirmation report (API query params / CLI)."""
    target_date: Optional[str] = None
    report_type: str = "file_confirmation"
    formats: List[str] = ["csv", "xlsx"]

class ReportGenerationResponse(BaseModel):
    success: bool
    message: str
    output_paths: List[str] = []
    record_count: int = 0
    errors: List[str] = []
