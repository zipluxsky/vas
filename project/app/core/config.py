import os
import json
import logging
from configparser import ConfigParser
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Union, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def _read_odbc_ini_section(odbc_ini_path: Path, section: str) -> Dict[str, Any]:
    """Read a DSN section from odbc.ini. Returns dict with host (Server), port (Port), database (Database)."""
    out: Dict[str, Any] = {}
    section = (section or "").strip() or "Sample"
    if not odbc_ini_path.exists():
        logger.debug(f"odbc.ini not found at {odbc_ini_path}")
        return out
    try:
        parser = ConfigParser()
        parser.read(odbc_ini_path, encoding="utf-8-sig")
        if not parser.has_section(section):
            for s in parser.sections():
                if s.strip() == section:
                    section = s
                    break
            else:
                logger.warning(f"odbc.ini has no section [{section}]; found: {parser.sections()}")
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
        
    def _pick_env_config(self, envs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select the best matching environment config. Tries ENVIRONMENT, then dev, prod, then first available."""
        for candidate in (self.ENVIRONMENT, "dev", "prod"):
            if candidate in envs:
                return envs[candidate]
        return next(iter(envs.values()), None) if envs else None

    def load_configs(self):
        """Load database and email configuration from datasource.json, odbc.ini, and email_config.json."""
        try:
            datasource_path = self.BASE_DIR.parent / "configs" / "python_config" / "datasource.json"
            odbc_candidates = [
                self.BASE_DIR.parent / "configs" / "sybase_config" / "odbc.ini",
                self.BASE_DIR / "configs" / "sybase_config" / "odbc.ini",
            ]
            if datasource_path.exists():
                with open(datasource_path, 'r') as f:
                    ds_data = json.load(f)

                # --- Sybase: database.sybase.<dsn_name>.<env> ---
                sybase_dsns = ds_data.get("database", {}).get("sybase", {})
                for dsn_name, envs in sybase_dsns.items():
                    env_config = self._pick_env_config(envs)
                    if env_config is None:
                        continue
                    self.db_config['sybase'] = {
                        'user': env_config.get('user'),
                        'password': env_config.get('password'),
                        'isql_path': env_config.get('isql_path') or 'isql',
                    }
                    dsn = (env_config.get('server') or dsn_name).strip()
                    logger.info("Sybase: env=%s, looking for odbc.ini section [%s]", self.ENVIRONMENT, dsn)
                    odbc = {}
                    for path in odbc_candidates:
                        odbc = _read_odbc_ini_section(path, dsn)
                        if odbc:
                            logger.info("Sybase: matched [%s] in %s → host=%s port=%s db=%s",
                                        dsn, path, odbc.get('host'), odbc.get('port'), odbc.get('database'))
                            break
                    for key, value in (odbc or {}).items():
                        if value is not None:
                            self.db_config['sybase'][key] = value
                    sb = self.db_config['sybase']
                    if not odbc or sb.get('host') is None or sb.get('port') is None or not sb.get('database'):
                        logger.warning(
                            "Sybase host/port/database missing: ensure odbc.ini exists at configs/sybase_config/odbc.ini "
                            "with a section matching datasource server value (e.g. [%s]) and Server, Port, Database keys",
                            dsn,
                        )
                    break

                # --- MySQL: mysql.<dsn_name>.<env> ---
                mysql_dsns = ds_data.get("mysql", {})
                for dsn_name, envs in mysql_dsns.items():
                    env_config = self._pick_env_config(envs)
                    if env_config is None:
                        continue
                    self.db_config['mysql'] = {
                        'user': env_config.get('user'),
                        'password': env_config.get('password'),
                    }
                    if env_config.get('server'):
                        self.db_config['mysql']['host'] = env_config['server']
                    if env_config.get('port') is not None:
                        self.db_config['mysql']['port'] = env_config['port']
                    if env_config.get('database'):
                        self.db_config['mysql']['database'] = env_config['database']
                    break
            else:
                logger.warning(f"Datasource config file not found at {datasource_path}")

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
