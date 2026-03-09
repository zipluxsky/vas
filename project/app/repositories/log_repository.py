import logging
from typing import Dict, Any
from datetime import datetime
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

class LogRepository(BaseRepository):
    """Repository for logging system events"""
    
    def log_event(self, event_data: Dict[str, Any]) -> bool:
        """Log an event to the tracking database"""
        try:
            event_type = event_data.get("event_type", "unknown")
            status = event_data.get("status", "pending")
            files_processed = event_data.get("files_processed", 0)
            
            self.db.execute_query(
                "INSERT INTO file_processing_logs (event_type, status, files_processed, created_at) VALUES (%s, %s, %s, %s)",
                (event_type, status, files_processed, datetime.now())
            )
            return True
        except Exception as e:
            logger.error(f"Error logging processing event: {e}")
            return False
