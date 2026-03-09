from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import logging
import os
import aiofiles
from pathlib import Path
from uuid import uuid4

from app.api.deps import get_db_service, verify_token
from app.services.db_service import DatabaseService
from app.schemas.report_models import ReportGenerationResponse
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Ensure upload directory exists
UPLOAD_DIR = settings.BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload-document", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "general",
    db_service: DatabaseService = Depends(get_db_service),
    token: dict = Depends(verify_token)
) -> Any:
    """
    Upload a document for front office processing and store it locally.
    """
    try:
        # Generate a unique filename to prevent collisions
        file_ext = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid4().hex}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save the file asynchronously
        size = 0
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                size += len(content)
                await out_file.write(content)
                
        logger.info(f"Saved file: {file.filename} as {unique_filename}, size: {size} bytes")
        
        # Log to database
        db_service.log_processing_event({
            "event_type": f"document_upload_{document_type}",
            "status": "success",
            "files_processed": 1
        })
        
        return {
            "status": "success",
            "original_filename": file.filename,
            "saved_filename": unique_filename,
            "document_type": document_type,
            "size": size,
            "path": str(file_path)
        }
    except Exception as e:
        logger.error(f"Error processing file upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to process uploaded file")
