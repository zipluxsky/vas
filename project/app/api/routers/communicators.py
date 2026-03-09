from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
import logging

from app.schemas.communicators import (
    CommunicatorResponse,
    CommunicatorCreate,
    ProcessingStatus
)
from app.api.deps import get_db_service, verify_token
from app.services.db_service import DatabaseService
from app.usecases.communicators import process_communicator_files

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[CommunicatorResponse])
async def get_communicators(
    skip: int = 0,
    limit: int = 100,
    db_service: DatabaseService = Depends(get_db_service),
    token: dict = Depends(verify_token)
) -> Any:
    """
    Retrieve all communicators.
    """
    try:
        communicators = db_service.get_communicators(skip=skip, limit=limit)
        return communicators
    except Exception as e:
        logger.error(f"Error fetching communicators: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/process", response_model=ProcessingStatus)
async def trigger_processing(
    token: dict = Depends(verify_token)
) -> Any:
    """
    Trigger the processing of communicator files in the background using Celery.
    """
    try:
        # Schedule the processing task via Celery
        task = process_communicator_files.delay()
        
        return ProcessingStatus(
            status="accepted",
            message=f"Processing task scheduled successfully with ID: {task.id}"
        )
    except Exception as e:
        logger.error(f"Error scheduling processing task: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule processing task")

@router.get("/{communicator_id}", response_model=CommunicatorResponse)
async def get_communicator(
    communicator_id: int,
    db_service: DatabaseService = Depends(get_db_service),
    token: dict = Depends(verify_token)
) -> Any:
    """
    Get a specific communicator by ID.
    """
    communicator = db_service.get_communicator_by_id(communicator_id)
    if not communicator:
        raise HTTPException(status_code=404, detail="Communicator not found")
    return communicator
