"""
Celery tasks that mirror front_office router logic so Option B (Airflow XML)
can trigger by router function names. API behaviour is unchanged.
"""
import logging
from typing import Any

from app.api.deps import get_db_service
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="upload_document")
def upload_document(
    document_type: str = "general",
    file_path: str | None = None,
    original_filename: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Celery task with the same name as the router endpoint.
    Runs the same post-upload logic (logging) so Option B can trigger by task name
    "upload_document" without changing the API. Optional kwargs allow passing
    path/filename when a file was staged elsewhere (e.g. by another job).
    """
    db_service = get_db_service()
    db_service.log_processing_event({
        "event_type": f"document_upload_{document_type}",
        "status": "success",
        "files_processed": 1,
    })
    logger.info(
        "upload_document task completed: document_type=%s path=%s original_filename=%s",
        document_type,
        file_path,
        original_filename,
    )
    return {
        "status": "success",
        "document_type": document_type,
        "file_path": file_path,
        "original_filename": original_filename,
    }
