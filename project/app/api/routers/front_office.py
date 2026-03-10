from __future__ import annotations

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.core.cli import expose_cli
from app.schemas.report_models import FileConfirmationInput
from app.usecases.reports import run_file_confirmation
from app.usecases.front_office_tasks import upload_document

router = APIRouter(
    tags=["front_office"],
    responses={404: {"description": "Not found"}},
)


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
    response_class=HTMLResponse,
    summary="File Confirmation report",
)
async def file_confirmation_endpoint(
    request: Request,
    cmd: FileConfirmationInput = Depends(get_file_confirmation_input),
):
    host = request.client.host if request.client else "0.0.0.0"
    out = await run_file_confirmation(cmd, host)
    return HTMLResponse(content=out, status_code=200)


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


# AUTO CLI — best practice: use --json for nested or long args; here it's flat so flags work well
expose_cli(
    name="file-confirmation",
    model=FileConfirmationInput,
    runner=lambda body: run_file_confirmation(body, host="cli"),
    group="reports",
    help="Generate File Confirmation report (same as GET .../front-office/file_confirmation).",
)
