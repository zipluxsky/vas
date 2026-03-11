import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings

def setup_logging(level=None):
    """Configure structured logging for the application"""
    if level is None:
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        
    # Create logs directory if it doesn't exist
    log_dir = settings.BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Define log format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = RotatingFileHandler(
        log_dir / "vascular.log", 
        maxBytes=10485760, # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # Separate file handler for errors
    error_handler = RotatingFileHandler(
        log_dir / "vascular_error.log",
        maxBytes=10485760,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)
    
    # Reduce noise from 3rd party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("mysql.connector").setLevel(logging.WARNING)
    
    # Log startup message
    logging.getLogger(__name__).info(
        f"Logging initialized at level {logging.getLevelName(level)}"
    )


class LogManager:
    """Per-request/per-operation log buffer for web/CLI (web_info, flush_web, close)."""

    def __init__(self, project: str = "", log_name: str = ""):
        self.project = project
        self.log_name = log_name
        self._lines: list = []

    def web_info(self, msg: str) -> None:
        self._lines.append(msg)
        logging.getLogger(__name__).info(f"[{self.log_name}] {msg}")

    def fastapi_log(self, msg, show_in_web: int = 1) -> None:
        if show_in_web:
            self._lines.append(str(msg))
        logging.getLogger(__name__).info(f"[{self.log_name}] {msg}")

    def flush_web(self) -> str:
        return "\n".join(self._lines)

    def gen_fastapi_log(self) -> str:
        return "<br>\n".join(self._lines)

    def close(self) -> None:
        self._lines.clear()
