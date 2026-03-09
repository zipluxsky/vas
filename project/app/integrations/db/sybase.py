import logging
from typing import Dict, Any, List, Optional
import pymssql

from app.integrations.db.base import BaseDatabase

logger = logging.getLogger(__name__)

class SybaseDatabase(BaseDatabase):
    """
    Sybase/SQL Server database connection implementation using pymssql.
    """
    
    def connect(self) -> bool:
        """Establish connection using pymssql"""
        try:
            if not self.connection:
                logger.info(f"Connecting to Sybase at {self.config.get('host')}")
                self.connection = pymssql.connect(
                    server=self.config.get('host'),
                    port=self.config.get('port', 1433),
                    user=self.config.get('user'),
                    password=self.config.get('password'),
                    database=self.config.get('database')
                )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Sybase: {e}")
            return False
        
    def disconnect(self):
        """Close the database connection"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Sybase: {e}")
            finally:
                self.connection = None
        
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute query using pymssql"""
        if not self.connection:
            if not self.connect():
                raise Exception("Database connection failed")
                
        logger.debug(f"Executing Sybase query: {query}")
        
        try:
            cursor = self.connection.cursor(as_dict=True)
            cursor.execute(query, params or ())
            # pymssql requires explicit fetchall for select queries
            # if it's not a select query, fetchall will raise an exception
            if cursor.description:
                result = cursor.fetchall()
            else:
                self.connection.commit()
                result = []
            cursor.close()
            return result
        except Exception as e:
            logger.error(f"Error executing Sybase query: {e}")
            raise
