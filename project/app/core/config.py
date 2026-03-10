import os
import json
import logging
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Vascular Document Processing"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-that-should-be-changed")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Base paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent.absolute()
    
    # These will be populated from config files
    db_config: Dict[str, Any] = {}
    email_config: Dict[str, Any] = {}
    
    class Config:
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_configs()
        
    def load_configs(self):
        """Load external configuration files"""
        try:
            config_path = self.BASE_DIR / "config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    self.db_config = data.get("db", {})
            else:
                logger.warning(f"Config file not found at {config_path}, using defaults")
                
            # Load datasource configuration (e.g. for sybase)
            datasource_path = self.BASE_DIR.parent / "configs" / "python_config" / "datasource.json"
            if datasource_path.exists():
                with open(datasource_path, 'r') as f:
                    ds_data = json.load(f)
                    db_root = ds_data.get("database", {})
                    for db_name, envs in db_root.items():
                        # Use self.ENVIRONMENT or fallback to dev
                        env = self.ENVIRONMENT if self.ENVIRONMENT in envs else "dev"
                        if env in envs:
                            env_config = envs[env]
                            if 'sybase' not in self.db_config:
                                self.db_config['sybase'] = {}
                            
                            self.db_config['sybase']['host'] = env_config.get('server')
                            self.db_config['sybase']['user'] = env_config.get('user')
                            self.db_config['sybase']['password'] = env_config.get('password')
                            self.db_config['sybase']['database'] = db_name
                            
                            # ISQL Path Override
                            if 'isql_path' in env_config:
                                self.db_config['sybase']['isql_path'] = env_config.get('isql_path')
                                
                            # Default port if not present
                            if 'port' not in self.db_config['sybase']:
                                self.db_config['sybase']['port'] = env_config.get('port')
                            break # Assume the first database definition applies to Sybase
            else:
                logger.warning(f"Datasource config file not found at {datasource_path}, using config.json defaults")
                    
            email_config_path = self.BASE_DIR.parent / "configs" / "python_config" / "email.json"
            if email_config_path.exists():
                with open(email_config_path, 'r') as f:
                    self.email_config = json.load(f)
            else:
                logger.warning(f"Email config file not found at {email_config_path}, using defaults")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON configuration: {e}")
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")

settings = Settings()
