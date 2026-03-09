import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from app.integrations.db.base import BaseDatabase

logger = logging.getLogger(__name__)

class MySQLDatabase(BaseDatabase):
    """MySQL database connection implementation using SQLAlchemy with Connection Pooling"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine = None
        
    def connect(self) -> bool:
        if self.engine is not None:
            return True
            
        try:
            user = self.config.get("user", "")
            password = self.config.get("password", "")
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 3306)
            database = self.config.get("database", "")
            
            # Using mysql+pymysql as the standard driver
            connection_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
            
            # Create engine with connection pooling
            self.engine = create_engine(
                connection_url,
                pool_size=self.config.get("pool_size", 5),
                max_overflow=self.config.get("max_overflow", 10),
                pool_pre_ping=True, # Test connections before using them
                pool_recycle=3600
            )
            
            # Test connection
            with self.engine.connect() as conn:
                pass
                
            return True
        except Exception as e:
            logger.error(f"Error connecting to MySQL with SQLAlchemy: {e}")
            self.engine = None
            return False
            
    def disconnect(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None
            
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        if not self.connect():
            raise Exception("Database connection failed")
            
        try:
            with self.engine.begin() as connection:
                # exec_driver_sql allows using raw DBAPI driver string format (e.g. %s)
                result = connection.exec_driver_sql(query, params or ())
                
                if result.returns_rows:
                    # Convert to list of dicts using mappings
                    return [dict(row._mapping) for row in result]
                return []
        except SQLAlchemyError as e:
            logger.error(f"Error executing MySQL query: {e}")
            raise
