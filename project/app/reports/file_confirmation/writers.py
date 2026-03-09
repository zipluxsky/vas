import os
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class BaseWriter:
    def __init__(self):
        self.output_dir = os.path.join(settings.BASE_DIR, "output", "reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def get_file_path(self, prefix: str, target_date: datetime, ext: str) -> str:
        date_str = target_date.strftime("%Y%m%d")
        filename = f"{prefix}_{date_str}.{ext}"
        return os.path.join(self.output_dir, filename)

class CSVWriter(BaseWriter):
    def write(self, data: List[Dict], prefix: str, target_date: datetime) -> Optional[str]:
        if not data:
            return None
            
        path = self.get_file_path(prefix, target_date, "csv")
        try:
            pd.DataFrame(data).to_csv(path, index=False)
            logger.info(f"Wrote CSV report to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")
            return None

class ExcelWriter(BaseWriter):
    def write(self, data: List[Dict], prefix: str, target_date: datetime) -> Optional[str]:
        if not data:
            return None
            
        path = self.get_file_path(prefix, target_date, "xlsx")
        try:
            pd.DataFrame(data).to_excel(path, index=False)
            logger.info(f"Wrote Excel report to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to write Excel: {e}")
            return None
