import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.routers import front_office, communicators
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.swagger.page import custom_openapi, get_openapi_schema_filtered_by_tags

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="VASCULAR - Document Management and Processing API"
)

# Custom OpenAPI customization if needed
app.openapi = custom_openapi(app)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation error handler to return cleaner error messages"""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Include routers
app.include_router(front_office.router, prefix=f"{settings.API_V1_STR}/front-office", tags=["front-office"])
app.include_router(communicators.router, prefix=f"{settings.API_V1_STR}/communicators", tags=["communicators"])

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": settings.VERSION}


# --- Separate Swagger docs by tag (communicators vs front-office) ---

@app.get(
    f"{settings.API_V1_STR}/openapi/communicators.json",
    include_in_schema=False,
)
async def openapi_communicators(request: Request):
    """OpenAPI schema for Communicators API only."""
    return get_openapi_schema_filtered_by_tags(request.app, ["communicators", "health"])


@app.get(
    f"{settings.API_V1_STR}/openapi/front-office.json",
    include_in_schema=False,
)
async def openapi_front_office(request: Request):
    """OpenAPI schema for Front Office API only."""
    return get_openapi_schema_filtered_by_tags(request.app, ["front-office", "health"])


@app.get("/docs/communicators", include_in_schema=False)
async def swagger_ui_communicators():
    """Standalone Swagger UI for Communicators API."""
    return get_swagger_ui_html(
        openapi_url=f"{settings.API_V1_STR}/openapi/communicators.json",
        title=f"{settings.PROJECT_NAME} – Communicators",
    )


@app.get("/docs/front-office", include_in_schema=False)
async def swagger_ui_front_office():
    """Standalone Swagger UI for Front Office API."""
    return get_swagger_ui_html(
        openapi_url=f"{settings.API_V1_STR}/openapi/front-office.json",
        title=f"{settings.PROJECT_NAME} – Front Office",
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
