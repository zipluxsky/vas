from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class CommunicatorBase(BaseModel):
    name: str
    type: str
    active: bool = True
    config: Optional[Dict[str, Any]] = None

class CommunicatorCreate(CommunicatorBase):
    pass

class CommunicatorResponse(CommunicatorBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ProcessingStatus(BaseModel):
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None
