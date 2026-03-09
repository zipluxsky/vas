from pydantic import BaseModel
from typing import Optional

class DatabaseConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: Optional[str] = None
    
class MySQLConfig(DatabaseConfig):
    port: int = 3306
    
class SybaseConfig(DatabaseConfig):
    port: int = 5000
    isql_path: str = "isql"
