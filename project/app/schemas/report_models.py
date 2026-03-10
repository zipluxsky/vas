from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class ReportGenerationRequest(BaseModel):
    target_date: Optional[str] = None
    report_type: str = "file_confirmation"
    formats: List[str] = ["csv", "xlsx"]

class FileConfirmationInput(BaseModel):
    """Input for File Confirmation report (API query params / CLI)."""
    trade_date: str = Field(default="19000101")
    cpty: str = Field(default="all")
    by: Literal["email", "download"] = "email"
    env: Literal["dev", "uat", "prod"] = "prod"
    versioning: str = "1"
    send_file: bool = True

class ReportGenerationResponse(BaseModel):
    success: bool
    message: str
    output_paths: List[str] = []
    record_count: int = 0
    errors: List[str] = []
