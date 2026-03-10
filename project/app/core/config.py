import os
import json
import logging
from configparser import ConfigParser
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Union, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def _read_odbc_ini_section(odbc_ini_path: Path, section: str) -> Dict[str, Any]:
    """Read a DSN section from odbc.ini. Returns dict with Server (host), Port (int), Database."""
    out: Dict[str, Any] = {}
    if not odbc_ini_path.exists():
        return out
    try:
        parser = ConfigParser()
        parser.read(odbc_ini_path, encoding="utf-8")
        if not parser.has_section(section):
            return out
        if parser.has_option(section, "Server"):
            out["host"] = parser.get(section, "Server").strip()
        if parser.has_option(section, "Port"):
            try:
                out["port"] = parser.getint(section, "Port")
            except ValueError:
                out["port"] = int(parser.get(section, "Port").strip())
        if parser.has_option(section, "Database"):
            out["database"] = parser.get(section, "Database").strip()
        return out
    except Exception as e:
        logger.warning(f"Could not read odbc.ini section [{section}]: {e}")
        return out

class Settings(BaseSettings):
    PROJECT_NAME: str = "Vascular Document Processing"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # JWT Settings — SECRET_KEY must be set via environment variable (no hardcoded default)
    SECRET_KEY: str = ""  # Set SECRET_KEY in environment; empty causes JWT auth to fail
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Attachments: only paths under this directory are allowed (prevents path traversal).
    # Set via ATTACHMENT_ALLOWED_DIR env or leave empty to reject path-based attachments from API.
    ATTACHMENT_ALLOWED_DIR: str = ""

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
                
            # Load datasource configuration (user/password) and odbc.ini (host, port, database)
            datasource_path = self.BASE_DIR.parent / "configs" / "python_config" / "datasource.json"
            odbc_ini_path = self.BASE_DIR.parent / "configs" / "sybase_config" / "odbc.ini"
            if datasource_path.exists():
                with open(datasource_path, 'r') as f:
                    ds_data = json.load(f)
                    db_root = ds_data.get("database", {})
                    for db_name, envs in db_root.items():
                        env = self.ENVIRONMENT if self.ENVIRONMENT in envs else "dev"
                        if env in envs:
                            env_config = envs[env]
                            if 'sybase' not in self.db_config:
                                self.db_config['sybase'] = {}
                            # User and password from datasource.json only
                            self.db_config['sybase']['user'] = env_config.get('user')
                            self.db_config['sybase']['password'] = env_config.get('password')
                            if 'isql_path' in env_config:
                                self.db_config['sybase']['isql_path'] = env_config.get('isql_path')
                            # Host, port, database from odbc.ini: datasource "server" value = odbc.ini section tag (e.g. "Sample" -> [Sample])
                            dsn = env_config.get('server', 'Sample')
                            odbc = _read_odbc_ini_section(odbc_ini_path, dsn)
                            for key, value in odbc.items():
                                if value is not None:
                                    self.db_config['sybase'][key] = value
                            break
            else:
                logger.warning(f"Datasource config file not found at {datasource_path}, using config.json defaults")
                    
            email_config_path = self.BASE_DIR.parent / "configs" / "python_config" / "email_config.json"
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
