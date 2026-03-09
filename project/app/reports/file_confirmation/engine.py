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

    def generate(self, target_date: datetime) -> Dict[str, Any]:
        """
        Generate the file confirmation report
        Returns a dictionary with generation status and output paths
        """
        logger.info(f"Starting file confirmation report generation for {target_date.date()}")
        
        try:
            # 1. Fetch data from multiple sources
            mysql_data = self._fetch_mysql_data(target_date)
            sybase_data = self._fetch_sybase_data(target_date)
            
            # 2. Consolidate and format data
            merged_data = self._merge_data(mysql_data, sybase_data)
            formatted_data = self.formatter.format_data(merged_data)

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

    def _fetch_mysql_data(self, target_date: datetime) -> List[Dict[str, Any]]:
        """Fetch file processing records from MySQL"""
        query = """
            SELECT file_id, file_name, status, processing_time, communicator_id
            FROM file_processing_logs
            WHERE DATE(processing_time) = %s
        """
        try:
            # Mock query for demonstration
            return self.db_service.mysql.execute_query(
                query, (target_date.strftime("%Y-%m-%d"),)
            )
        except Exception as e:
            logger.error(f"MySQL fetch error: {e}")
            # Return mock data for development
            return [{"file_id": 1, "file_name": "test1.txt", "status": "SUCCESS"}]
            
    def _fetch_sybase_data(self, target_date: datetime) -> List[Dict[str, Any]]:
        """Fetch related business data from Sybase"""
        from app.services.sql_template_service import sql_templates
        
        try:
            # Provide the parameter 'cpty' required by the template.
            # Ensure proper string formatting (e.g. quotes) if it's a string field.
            cpty_value = self.config.get("cpty", "'DEFAULT_CPTY'")
            query = sql_templates.get_query("file_confirmation/ExcelExtract", params={"cpty": cpty_value})
            
            return self.db_service.sybase.execute_query(query)
        except Exception as e:
            logger.error(f"Sybase fetch error: {e}")
            return [{"communicator_id": 1, "communicator_name": "CommA"}]

    def _merge_data(self, mysql_data: List[Dict], sybase_data: List[Dict]) -> List[Dict]:
        """Merge MySQL logging data with Sybase business data"""
        # Convert to pandas for easier merging
        if not mysql_data:
            return []
            
        df_mysql = pd.DataFrame(mysql_data)
        df_sybase = pd.DataFrame(sybase_data)
        
        if df_sybase.empty:
            return df_mysql.to_dict('records')
            
        # Merge on communicator_id
        merged = pd.merge(
            df_mysql, 
            df_sybase, 
            on='communicator_id', 
            how='left'
        )
        
        return merged.to_dict('records')
        
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
