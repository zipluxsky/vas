import copy
from typing import List

from fastapi.openapi.utils import get_openapi


def get_openapi_schema_filtered_by_tags(app, include_tags: List[str]):
    """
    Return a copy of the app's OpenAPI schema containing only paths whose operations
    have at least one tag in include_tags. Used for separate Swagger docs per tag group.
    """
    full = app.openapi()
    schema = copy.deepcopy(full)
    paths = schema.get("paths", {})
    new_paths = {}
    for path_key, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        new_path_item = {}
        for key, value in path_item.items():
            if key in ("get", "post", "put", "patch", "delete", "head", "options", "trace"):
                if isinstance(value, dict) and set(value.get("tags", [])) & set(include_tags):
                    new_path_item[key] = value
            else:
                new_path_item[key] = value
        if any(k in new_path_item for k in ("get", "post", "put", "patch", "delete", "head", "options", "trace")):
            new_paths[path_key] = new_path_item
    schema["paths"] = new_paths
    schema["tags"] = [t for t in schema.get("tags", []) if isinstance(t, dict) and t.get("name") in include_tags]
    return schema


def custom_openapi(app):
    """Generate custom OpenAPI schema for Swagger UI"""
    def _custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
            
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add custom logo or modifications here
        openapi_schema["info"]["x-logo"] = {
            "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
        }

        # Ensure security schemes are defined
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
            
        if "securitySchemes" not in openapi_schema["components"]:
            openapi_schema["components"]["securitySchemes"] = {
                "OAuth2PasswordBearer": {
                    "type": "oauth2",
                    "flows": {
                        "password": {
                            "scopes": {},
                            "tokenUrl": f"{app.openapi_url.replace('/openapi.json', '')}/login/access-token"
                        }
                    }
                }
            }

        # Apply security globally
        openapi_schema["security"] = [{"OAuth2PasswordBearer": []}]
        
        # Organize tags
        openapi_schema["tags"] = [
            {
                "name": "front-office",
                "description": "Operations related to front office document ingestion"
            },
            {
                "name": "communicators",
                "description": "Manage and process communicators"
            },
            {
                "name": "health",
                "description": "System health checks"
            }
        ]

        app.openapi_schema = openapi_schema
        return app.openapi_schema
        
    return _custom_openapi
