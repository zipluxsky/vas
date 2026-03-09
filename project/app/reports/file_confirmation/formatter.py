import logging
from typing import Dict, Any, List
import pandas as pd

logger = logging.getLogger(__name__)

class FileConfirmationFormatter:
    """Formats raw data into the structure required for the report"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Default column mapping if none provided
        self.column_mapping = self.config.get("column_mapping", {
            "file_name": "File Name",
            "communicator_name": "Communicator",
            "status": "Processing Status",
            "processing_time": "Time Processed"
        })
        
        # Columns to exclude from final report
        self.exclude_columns = self.config.get("exclude_columns", [
            "file_id", "communicator_id"
        ])

    def format_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply formatting rules to the data"""
        if not data:
            return []
            
        try:
            df = pd.DataFrame(data)
            
            # Drop excluded columns if they exist
            cols_to_drop = [col for col in self.exclude_columns if col in df.columns]
            if cols_to_drop:
                df = df.drop(columns=cols_to_drop)
                
            # Rename columns based on mapping
            rename_dict = {k: v for k, v in self.column_mapping.items() if k in df.columns}
            if rename_dict:
                df = df.rename(columns=rename_dict)
                
            # Format date/time columns if they exist
            time_col = self.column_mapping.get("processing_time", "Time Processed")
            if time_col in df.columns:
                try:
                    df[time_col] = pd.to_datetime(df[time_col]).dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    logger.debug(f"Could not format time column: {e}")

            # Sort if specified
            sort_by = self.config.get("sort_by")
            if sort_by and sort_by in df.columns:
                ascending = self.config.get("sort_ascending", True)
                df = df.sort_values(by=sort_by, ascending=ascending)
                
            # Fill missing values
            df = df.fillna(self.config.get("fill_na", "N/A"))
            
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error formatting data: {e}")
            # Return original data if formatting fails
            return data
