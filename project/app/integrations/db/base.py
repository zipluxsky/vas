from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseDatabase(ABC):
    """Abstract base class for all database connections"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the database"""
        pass
        
    @abstractmethod
    def disconnect(self):
        """Close the database connection"""
        pass
        
    @abstractmethod
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a read query and return results"""
        pass
