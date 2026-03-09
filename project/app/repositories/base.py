from typing import Generic, TypeVar, List, Optional, Any, Dict
from app.integrations.db.base import BaseDatabase

class BaseRepository:
    """Base repository class"""
    
    def __init__(self, db: BaseDatabase):
        self.db = db
