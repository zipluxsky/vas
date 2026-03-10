from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_email_service
from app.services.email_service import EmailService
from app.schemas.communicators import MatrixSendRequest

# CLI registry + runner
from app.core.cli import expose_cli
from app.usecases.communicators import run_email_sender, process_communicator_files

# logging
from app.core.logging import LogManager

router = APIRouter(
    tags=["communicators"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/email_sender",
    summary="Send email using matrix configuration",
    response_model=dict,
)
async def email_sender(
    body: MatrixSendRequest,
    svc: EmailService = Depends(get_email_service),
):
    """
    Uses DI to send the email via the matrix configuration.
    """
    log = LogManager(project=body.project, log_name="email_sender")
    try:
        log.web_info("Starting email sender")
        await svc.send(
            project=body.project,
            function=body.function,
            html_body=body.html_body,
            env=body.env,
            subject_suffix=body.subject_suffix,
            attachments=body.attachments,
        )
        log.web_info("Email sent OK")

        return {"ok": True, "log": log.flush_web()}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {e}",
        )
    finally:
        log.close()


@router.get("/ping", summary="Communicators health")
async def ping():
    return {"status": "ok"}


@router.post(
    "/process",
    summary="Trigger communicator files processing (enqueues Celery task)",
    response_model=dict,
    status_code=202,
)
async def process():
    """
    Enqueues process_communicator_files on Vascular's Celery worker.
    Used by Airflow (Option A: HTTP trigger). Returns task_id for polling.
    """
    result = process_communicator_files.delay()
    return {"ok": True, "task_id": result.id}


# --- AUTO-REGISTER CLI on module import ---
expose_cli(
    name="email-sender",
    model=MatrixSendRequest,
    runner=run_email_sender,
    group="communicators",
    help="Send email using matrix configuration (same as POST /communicators/email_sender).",
)
