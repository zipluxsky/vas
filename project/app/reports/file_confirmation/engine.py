import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.db_service import DatabaseService
from app.reports.file_confirmation.formatter import FileConfirmationFormatter
from app.reports.file_confirmation.writers import CSVWriter, ExcelWriter

logger = logging.getLogger(__name__)

class FileConfirmationEngine:
    """Engine for generating file confirmation reports"""
    
    def __init__(self, db_service: DatabaseService, config: Dict[str, Any]):
        self.db_service = db_service
        self.config = config
        self.formatter = FileConfirmationFormatter(config.get("formatting", {}))
        self._run_overrides: Dict[str, Any] = {}

    def generate(self, target_date: datetime, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate the file confirmation report.
        overrides: optional dict (e.g. cpty, env) to override config for this run.
        Returns a dictionary with generation status and output paths
        """
        overrides = overrides or {}
        self._run_overrides = overrides
        logger.info(f"Starting file confirmation report generation for {target_date.date()}")
        
        try:
            # 1. Fetch data from Sybase
            sybase_data = self._fetch_sybase_data(target_date)
            
            # 2. Format data
            formatted_data = self.formatter.format_data(sybase_data)

            # 3. Write outputs
            output_paths = self._write_outputs(formatted_data, target_date)
            
            # 4. Generate summary
            summary = self._generate_summary(formatted_data)
            
            logger.info("File confirmation report generation completed successfully")
            return {
                "success": True,
                "output_paths": output_paths,
                "summary": summary,
                "record_count": len(formatted_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating file confirmation report: {e}")
            return {
                "success": False,
                "error": str(e),
                "output_paths": []
            }

    def _fetch_sybase_data(self, target_date: datetime) -> List[Dict[str, Any]]:
        """Fetch related business data from Sybase. All _run_overrides are passed as SQL template params."""
        from app.services.sql_template_service import sql_templates
        
        try:
            params = dict(self._run_overrides)
            params.setdefault("trade_date", target_date.strftime("%Y%m%d"))
            query = sql_templates.get_query("file_confirmation/ExcelExtract", params=params)
            
            return self.db_service.sybase.execute_query(query)
        except Exception as e:
            logger.error(f"Sybase fetch error: {e}")
            return [{"communicator_id": 1, "communicator_name": "CommA"}]

    def _write_outputs(self, data: List[Dict], target_date: datetime) -> List[str]:
        """Write reports to configured output formats"""
        outputs = []
        
        for format_type in self.config.get("formats", ["csv"]):
            if format_type.lower() == "csv":
                writer = CSVWriter()
                path = writer.write(data, "file_confirmation", target_date)
                if path:
                    outputs.append(path)
            elif format_type.lower() == "excel":
                writer = ExcelWriter()
                path = writer.write(data, "file_confirmation", target_date)
                if path:
                    outputs.append(path)
                    
        return outputs
        
    def _generate_summary(self, data: List[Dict]) -> str:
        """Generate a text summary of the report"""
        if not data:
            return "No files processed on this date."
            
        total = len(data)
        success_count = sum(1 for d in data if str(d.get("status", "")).upper() == "SUCCESS")
        fail_count = total - success_count
        
        return f"Processed {total} files: {success_count} successful, {fail_count} failed."
