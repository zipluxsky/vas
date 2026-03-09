from fastapi.openapi.utils import get_openapi

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
