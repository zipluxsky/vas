import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.integrations.db.base import BaseDatabase
from app.repositories.communicator_repository import CommunicatorRepository
from app.repositories.log_repository import LogRepository

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service layer that coordinates between different repositories"""
    
    def __init__(self, mysql_db: BaseDatabase, sybase_db: BaseDatabase):
        # Keep properties for backward compatibility with FileConfirmationEngine
        self.mysql = mysql_db
        self.sybase = sybase_db
        
        # Initialize repositories
        self.communicator_repo = CommunicatorRepository(sybase_db)
        self.log_repo = LogRepository(mysql_db)
        
    def get_communicators(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get communicators from Sybase"""
        return self.communicator_repo.get_all(skip=skip, limit=limit)
            
    def get_communicator_by_id(self, communicator_id: int) -> Optional[Dict[str, Any]]:
        """Get specific communicator by ID"""
        return self.communicator_repo.get_by_id(communicator_id)
        
    def log_processing_event(self, event_data: Dict[str, Any]) -> bool:
        """Log an event to MySQL tracking database"""
        return self.log_repo.log_event(event_data)
