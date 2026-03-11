from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from app.core.cli import expose_cli
from app.schemas.report_models import FileConfirmationInput
from app.usecases.reports import run_file_confirmation
from app.usecases.front_office_tasks import upload_document

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["front_office"],
    responses={404: {"description": "Not found"}},
)

_MEDIA_TYPES = {
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}


def get_file_confirmation_input(
    trade_date: str = Query("19000101", description="Trade date YYYYMMDD"),
    cpty: str = Query("all", description="Counterparty filter"),
    by: str = Query("email", description="Delivery: email or download"),
    env: str = Query("prod", description="Environment: dev, uat, prod"),
    versioning: str = Query("1", description="Report versioning"),
    send_file: bool = Query(True, description="Whether to send file (e.g. by email)"),
) -> FileConfirmationInput:
    return FileConfirmationInput(
        trade_date=trade_date,
        cpty=cpty,
        by=by,
        env=env,
        versioning=versioning,
        send_file=send_file,
    )


@router.get(
    "/file_confirmation",
    summary="File Confirmation report",
    responses={
        200: {
            "description": "Report HTML (by=email) or downloadable file (by=download)",
            "content": {
                "text/html": {},
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            },
        }
    },
)
async def file_confirmation_endpoint(
    request: Request,
    cmd: FileConfirmationInput = Depends(get_file_confirmation_input),
):
    host = request.client.host if request.client else "0.0.0.0"
    result = await run_file_confirmation(cmd, host)

    if cmd.by == "download" and result.get("output_paths"):
        file_path = result["output_paths"][0]
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            media_type = _MEDIA_TYPES.get(ext, "application/octet-stream")
            return FileResponse(
                path=file_path,
                filename=os.path.basename(file_path),
                media_type=media_type,
            )
        logger.warning("Download requested but file not found: %s", file_path)

    return HTMLResponse(content=result.get("html", ""), status_code=200)


class TriggerUploadDocumentBody(BaseModel):
    """Optional body for trigger-upload-document (Option A HTTP trigger)."""
    document_type: str = "general"
    file_path: str | None = None
    original_filename: str | None = None


@router.post(
    "/trigger-upload-document",
    summary="Trigger upload_document Celery task (Option A: HTTP)",
    response_model=dict,
    status_code=202,
)
async def trigger_upload_document(body: TriggerUploadDocumentBody | None = None):
    """
    Enqueues the upload_document Celery task on Vascular's worker.
    Used by Airflow when triggering via HTTP (Option A) instead of shared broker.
    """
    b = body or TriggerUploadDocumentBody()
    result = upload_document.delay(
        document_type=b.document_type,
        file_path=b.file_path,
        original_filename=b.original_filename,
    )
    return {"ok": True, "task_id": result.id}


async def _cli_runner(body: FileConfirmationInput) -> str:
    result = await run_file_confirmation(body, host="cli")
    if body.by == "download" and result.get("output_paths"):
        return f"File saved to: {result['output_paths'][0]}"
    return result.get("html", "")

expose_cli(
    name="file-confirmation",
    model=FileConfirmationInput,
    runner=_cli_runner,
    group="reports",
    help="Generate File Confirmation report (same as GET .../front-office/file_confirmation).",
)
