import os
import re
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

class SqlTemplateService:
    """Service to load and format SQL queries from template files"""
    
    def __init__(self, template_dirs: Optional[List[Path]] = None):
        if template_dirs is None:
            self.template_dirs = [
                settings.BASE_DIR / "app" / "sql_templates",
                settings.BASE_DIR.parent / "data" / "sql"
            ]
        else:
            self.template_dirs = template_dirs
            
    def get_query(self, template_name: str, params: Dict[str, Any] = None) -> str:
        """
        Load a SQL template and substitute parameters.
        Parameters are expected in the format ${param_name} or {param_name}
        """
        template_path = None
        extensions = ['.template', '.sql', '']
        
        for base_dir in self.template_dirs:
            if base_dir is None:
                continue
            for ext in extensions:
                # Resolve the path to allow subdirectories like "file_confirmation/ExcelExtract"
                path = base_dir / f"{template_name}{ext}"
                if path.exists():
                    template_path = path
                    break
            if template_path:
                break
                
        if not template_path:
            raise FileNotFoundError(f"SQL template '{template_name}' not found in any of {self.template_dirs}")

        with open(template_path, 'r', encoding='utf-8') as f:
            query = f.read()
            
        if params:
            for key, value in params.items():
                # Note: this relies on the ISQLDatabase escaping layer or caller to secure variables if needed.
                # However, our ISQLDatabase uses parameterized queries with execute_query(sql, params).
                # Wait, if we replace here, it defeats parameterized queries! 
                # If the caller provides params, we replace them. 
                # To be safe from injection, the caller could use get_query(name) and pass params to execute_query.
                # But since the template HAS {cpty}, we MUST replace it if we want to follow the file.
                query = query.replace(f"${{{key}}}", str(value))
                query = query.replace(f"{{{key}}}", str(value))
                query = query.replace(f"###{key}###", str(value))
                
        # Check for unreplaced parameters
        unreplaced_shell = re.findall(r'\$\{([^}]+)\}', query)
        unreplaced_braces = re.findall(r'(?<!\$)\{([a-zA-Z0-9_]+)\}', query)
        
        all_unreplaced = unreplaced_shell + unreplaced_braces
        if all_unreplaced:
            logger.debug(f"Potentially unreplaced parameters in SQL template {template_name}: {all_unreplaced}")
            
        return query

# Create a default instance
sql_templates = SqlTemplateService()
