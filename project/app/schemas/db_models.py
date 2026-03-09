from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FileProcessingLog(BaseModel):
    file_id: int
    file_name: str
    status: str
    processing_time: datetime
    communicator_id: int
    error_message: Optional[str] = None

class CommunicatorData(BaseModel):
    communicator_id: int
    communicator_name: str
    type: str
    active: bool
