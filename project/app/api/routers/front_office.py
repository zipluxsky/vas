from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse

from app.core.cli import expose_cli
from app.schemas.report_models import FileConfirmationInput
from app.usecases.reports import run_file_confirmation

router = APIRouter(
    tags=["front_office"],
    responses={404: {"description": "Not found"}},
)


def get_file_confirmation_input(
    target_date: Optional[str] = Query(None, description="Target date YYYY-MM-DD"),
    report_type: str = Query("file_confirmation"),
    formats: str = Query("csv,xlsx", description="Comma-separated: csv,xlsx"),
) -> FileConfirmationInput:
    return FileConfirmationInput(
        target_date=target_date,
        report_type=report_type,
        formats=formats.split(",") if formats else ["csv", "xlsx"],
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


# AUTO CLI — best practice: use --json for nested or long args; here it's flat so flags work well
expose_cli(
    name="file-confirmation",
    model=FileConfirmationInput,
    runner=lambda body: run_file_confirmation(body, host="cli"),
    group="reports",
    help="Generate File Confirmation report (same as GET .../front-office/file_confirmation).",
)
