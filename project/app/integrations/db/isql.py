import logging
from typing import Dict, Any, List, Optional
import subprocess
import tempfile
import os
import csv
import datetime

from app.integrations.db.base import BaseDatabase

logger = logging.getLogger(__name__)

class ISQLDatabase(BaseDatabase):
    """
    Sybase connection implementation using the isql command line tool.
    This acts as a wrapper around isql since native drivers can be problematic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get("host")
        self.port = config.get("port")
        self.user = config.get("user")
        self.password = config.get("password")
        self.database = config.get("database")
        self.isql_path = config.get("isql_path") or "isql"

    def connect(self) -> bool:
        """Test the connection by running a simple query. Returns False if config is incomplete."""
        if not self.host or self.port is None or not self.user or not self.database:
            logger.warning(
                "Sybase/ISQL config incomplete: host, port, user and database are required; skipping connection"
            )
            return False
        try:
            result = self._run_isql("SELECT 1")
            return "1" in result or bool(result)
        except Exception as e:
            logger.error(f"Failed to connect via isql: {e}")
            return False
            
    def disconnect(self):
        """No persistent connection to close for CLI wrapper"""
        pass
        
    def _create_temp_sql_file(self, query: str) -> str:
        """Create a temporary file with the SQL query"""
        fd, path = tempfile.mkstemp(suffix=".sql")
        with os.fdopen(fd, 'w') as f:
            # Add database selection if specified
            if self.database:
                f.write(f"USE {self.database}\nGO\n")
            f.write(f"{query}\nGO\n")
        return path

    def _run_isql(self, query: str) -> str:
        """Execute query using isql command line"""
        sql_file = self._create_temp_sql_file(query)
        
        try:
            # Construct command: isql -U user -P password -S server -i input_file -s ","
            # -s "," sets output separator to comma for easier parsing
            cmd = [
                self.isql_path,
                "-U", self.user or "",
                "-P", self.password or "",
                "-S", f"{self.host}:{self.port}" if self.port else (self.host or ""),
                "-i", sql_file,
                "-s", ",",
                "-w", "2000"
            ]
            
            logger.debug(f"Executing ISQL command for query: {query[:50]}...")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"ISQL error: {result.stderr}")
                raise Exception(f"ISQL execution failed: {result.stderr}")
                
            return result.stdout
            
        finally:
            # Clean up temp file
            if os.path.exists(sql_file):
                os.remove(sql_file)

    def _format_query(self, query: str, params: tuple = None) -> str:
        """
        Safely formats a SQL query by replacing ? placeholders with escaped parameters.
        """
        if not params:
            return query
            
        formatted_query = query
        for p in params:
            if p is None:
                formatted_query = formatted_query.replace('?', "NULL", 1)
            elif isinstance(p, bool):
                formatted_query = formatted_query.replace('?', "1" if p else "0", 1)
            elif isinstance(p, (int, float)):
                formatted_query = formatted_query.replace('?', str(p), 1)
            elif isinstance(p, (datetime.datetime, datetime.date)):
                formatted_query = formatted_query.replace('?', f"'{p.isoformat()}'", 1)
            elif isinstance(p, str):
                # Escape single quotes to prevent SQL injection
                escaped_p = p.replace("'", "''")
                formatted_query = formatted_query.replace('?', f"'{escaped_p}'", 1)
            else:
                # Fallback for other types
                escaped_p = str(p).replace("'", "''")
                formatted_query = formatted_query.replace('?', f"'{escaped_p}'", 1)
                
        return formatted_query

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Execute query and parse CSV-like output.
        """
        if not self.host or self.port is None or not self.user or not self.database:
            raise Exception(
                f"Sybase config incomplete (host={self.host}, port={self.port}, "
                f"user={'set' if self.user else None}, database={self.database})"
            )
        formatted_query = self._format_query(query, params)
        output = self._run_isql(formatted_query)
        return self._parse_isql_output(output)
        
    def _parse_isql_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse the custom output from isql into dictionaries"""
        if not output:
            return []
            
        # ISQL output typically includes headers, a separator line, and data
        # We need to filter out empty lines and the separator line (e.g., '---,---')
        lines = [line for line in output.split('\n') if line.strip()]
        
        if not lines:
            return []
            
        # Filter out informational lines like "return status = 0" or "(X rows affected)"
        filtered_lines = []
        for line in lines:
            lower_line = line.lower().strip()
            if lower_line.startswith("return status") or lower_line.endswith("rows affected)"):
                continue
            filtered_lines.append(line)
            
        if not filtered_lines:
            return []
            
        # Check if the second line is a separator line (all dashes and commas)
        if len(filtered_lines) > 1 and all(c in '-,' or c.isspace() for c in filtered_lines[1]):
            # Remove the separator line
            filtered_lines.pop(1)
            
        try:
            import io
            # Use csv.DictReader to parse the remaining lines
            reader = csv.DictReader(io.StringIO('\n'.join(filtered_lines)), delimiter=',')
            return [
                {k.strip(): v.strip() if isinstance(v, str) else v 
                 for k, v in row.items() if k and k.strip()}
                for row in reader
            ]
        except Exception as e:
            logger.error(f"Error parsing ISQL output: {e}")
            return [{"raw_output": output}]
