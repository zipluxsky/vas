import logging
from typing import Dict, Any, List, Optional
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

class CommunicatorRepository(BaseRepository):
    """Repository for Communicator data"""
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get communicators with pagination"""
        try:
            return self.db.execute_query(
                "SELECT * FROM communicators ORDER BY id OFFSET %s ROWS FETCH NEXT %s ROWS ONLY", 
                (skip, limit)
            )
        except Exception as e:
            logger.error(f"Error fetching communicators: {e}")
            return []
            
    def get_by_id(self, communicator_id: int) -> Optional[Dict[str, Any]]:
        """Get specific communicator by ID"""
        try:
            results = self.db.execute_query(
                "SELECT * FROM communicators WHERE id = %s", 
                (communicator_id,)
            )
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error fetching communicator by ID: {e}")
            return None
