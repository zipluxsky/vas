import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

class ReportConfigLoader:
    """Loader for report-specific configurations"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            self.config_dir = settings.BASE_DIR / "configs" / "reports"
        else:
            self.config_dir = config_dir
            
    def load_report_config(self, report_name: str) -> Dict[str, Any]:
        """Load configuration for a specific report"""
        config_path = self.config_dir / f"{report_name}.json"
        
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found: {config_path}")
            return {}

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.debug(f"Loaded config for report {report_name}")
                return config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config file {config_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading config {config_path}: {e}")
            return {}

# Global instance for easy import
report_config_loader = ReportConfigLoader()
