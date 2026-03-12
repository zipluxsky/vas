"""
Celery tasks that mirror front_office router logic so Option B (Airflow XML)
can trigger by router function names. API behaviour is unchanged.

Pipeline tasks (fc_prepare_config … fc_send_email) break the monolithic
file_confirmation flow into 6 independently tracked steps. Intermediate
data is stored in Redis via PipelineContext.
"""
import asyncio
import logging
from typing import Any

from app.api.deps import get_db_service, get_email_service
from app.core.celery_app import celery_app
from app.core.pipeline_context import PipelineContext

logger = logging.getLogger(__name__)


def _log_step(step: str, pipeline_key: str, trace: dict | None, msg: str = "started") -> None:
    t = trace or {}
    logger.info(
        "pipeline %s %s | key=%s dag_run=%s",
        step, msg, pipeline_key, t.get("dag_run_id", "n/a"),
    )


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


@celery_app.task(name="file_confirmation", bind=True, max_retries=3, default_retry_delay=60)
def file_confirmation(
    self,
    trade_date: str = "19000101",
    cpty: str = "all",
    by: str = "email",
    env: str = "prod",
    versioning: str = "1",
    send_file: bool = True,
    _trace: dict[str, str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Celery task wrapping the file_confirmation report engine.
    Accepts the same parameters as FileConfirmationInput so Airflow
    (Option B with wait=true) can trigger and track the result.
    """
    from app.schemas.report_models import FileConfirmationInput
    from app.usecases.reports import run_file_confirmation

    trace = _trace or {}
    logger.info(
        "file_confirmation task started | trade_date=%s cpty=%s dag_run=%s",
        trade_date,
        cpty,
        trace.get("dag_run_id", "n/a"),
    )

    cmd = FileConfirmationInput(
        trade_date=trade_date,
        cpty=cpty,
        by=by,
        env=env,
        versioning=versioning,
        send_file=send_file,
    )
    try:
        result = asyncio.run(run_file_confirmation(cmd, host="celery"))
    except Exception as exc:
        logger.exception("file_confirmation task failed, retrying: %s", exc)
        raise self.retry(exc=exc)

    logger.info(
        "file_confirmation task completed | trade_date=%s cpty=%s success=%s dag_run=%s",
        trade_date,
        cpty,
        result.get("success"),
        trace.get("dag_run_id", "n/a"),
    )
    return result


# ======================================================================
# Pipeline tasks – 6 steps for file_confirmation
# ======================================================================

@celery_app.task(name="fc_prepare_config", bind=True, max_retries=2, default_retry_delay=30)
def fc_prepare_config(
    self,
    pipeline_key: str,
    trade_date: str = "19000101",
    cpty: str = "all",
    by: str = "email",
    env: str = "prod",
    versioning: str = "1",
    send_file: str = "true",
    _trace: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Step 1: date handling, load configs, filter counterparties."""
    _log_step("fc_prepare_config", pipeline_key, _trace)
    from app.reports.file_confirmation.engine import FileConfirmationEngine

    engine = FileConfirmationEngine(get_db_service(env=env))
    cmd_dict = {
        "trade_date": trade_date, "cpty": cpty, "by": by,
        "env": env, "versioning": versioning,
        "send_file": str(send_file).lower() not in ("false", "0", "no"),
    }
    try:
        result = engine.prepare_config(cmd_dict)
    except Exception as exc:
        raise self.retry(exc=exc)

    ctx = PipelineContext(pipeline_key)
    ctx.write("prepare_config", result)
    _log_step("fc_prepare_config", pipeline_key, _trace, "completed")
    return {"pipeline_key": pipeline_key, "step": "prepare_config", "status": "success"}


@celery_app.task(name="fc_prepare_sql", bind=True, max_retries=2, default_retry_delay=30)
def fc_prepare_sql(
    self,
    pipeline_key: str,
    _trace: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Step 2: render SQL template from config context."""
    _log_step("fc_prepare_sql", pipeline_key, _trace)
    from app.reports.file_confirmation.engine import FileConfirmationEngine

    ctx = PipelineContext(pipeline_key)
    config_ctx = ctx.read("prepare_config")

    engine = FileConfirmationEngine(
        get_db_service(env=config_ctx.get("cmd", {}).get("env", "prod"))
    )
    try:
        result = engine.prepare_sql(config_ctx)
    except Exception as exc:
        raise self.retry(exc=exc)

    ctx.write("prepare_sql", result)
    _log_step("fc_prepare_sql", pipeline_key, _trace, "completed")
    return {"pipeline_key": pipeline_key, "step": "prepare_sql", "status": "success"}


@celery_app.task(name="fc_run_query", bind=True, max_retries=2, default_retry_delay=60)
def fc_run_query(
    self,
    pipeline_key: str,
    _trace: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Step 3: execute SQL query against database."""
    _log_step("fc_run_query", pipeline_key, _trace)
    from app.reports.file_confirmation.engine import FileConfirmationEngine

    ctx = PipelineContext(pipeline_key)
    sql_ctx = ctx.read("prepare_sql")
    config_ctx = ctx.read("prepare_config")

    engine = FileConfirmationEngine(
        get_db_service(env=config_ctx.get("cmd", {}).get("env", "prod"))
    )
    try:
        result = engine.run_query(sql_ctx)
    except Exception as exc:
        raise self.retry(exc=exc)

    ctx.write("run_query", result)
    _log_step("fc_run_query", pipeline_key, _trace, "completed")
    return {"pipeline_key": pipeline_key, "step": "run_query", "status": "success"}


@celery_app.task(name="fc_parse_data", bind=True, max_retries=2, default_retry_delay=30)
def fc_parse_data(
    self,
    pipeline_key: str,
    _trace: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Step 4: parse raw SQL output, remove already-sent allocations."""
    _log_step("fc_parse_data", pipeline_key, _trace)
    from app.reports.file_confirmation.engine import FileConfirmationEngine

    ctx = PipelineContext(pipeline_key)
    query_ctx = ctx.read("run_query")
    config_ctx = ctx.read("prepare_config")

    engine = FileConfirmationEngine(
        get_db_service(env=config_ctx.get("cmd", {}).get("env", "prod"))
    )
    try:
        result = engine.parse_data(query_ctx, config_ctx)
    except Exception as exc:
        raise self.retry(exc=exc)

    ctx.write("parse_data", result)
    _log_step("fc_parse_data", pipeline_key, _trace, "completed")
    return {"pipeline_key": pipeline_key, "step": "parse_data", "status": "success"}


@celery_app.task(name="fc_generate_report", bind=True, max_retries=2, default_retry_delay=60)
def fc_generate_report(
    self,
    pipeline_key: str,
    _trace: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Step 5: per-counterparty formatting, group processing, HTML summary."""
    _log_step("fc_generate_report", pipeline_key, _trace)
    from app.reports.file_confirmation.engine import FileConfirmationEngine

    ctx = PipelineContext(pipeline_key)
    data_ctx = ctx.read("parse_data")
    config_ctx = ctx.read("prepare_config")

    engine = FileConfirmationEngine(
        get_db_service(env=config_ctx.get("cmd", {}).get("env", "prod"))
    )
    try:
        result = engine.generate_report(data_ctx, config_ctx)
    except Exception as exc:
        raise self.retry(exc=exc)

    ctx.write("generate_report", result)
    _log_step("fc_generate_report", pipeline_key, _trace, "completed")
    return {"pipeline_key": pipeline_key, "step": "generate_report", "status": "success"}


@celery_app.task(name="fc_send_email", bind=True, max_retries=2, default_retry_delay=60)
def fc_send_email(
    self,
    pipeline_key: str,
    _trace: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Step 6: send report via email using generated file paths and HTML body."""
    _log_step("fc_send_email", pipeline_key, _trace)

    ctx = PipelineContext(pipeline_key)
    report_ctx = ctx.read("generate_report")
    config_ctx = ctx.read("prepare_config")
    cmd = config_ctx.get("cmd", {})

    output_paths = report_ctx.get("output_paths", [])
    html_body = report_ctx.get("html_body", "")
    by = cmd.get("by", "email")
    send_file = cmd.get("send_file", True)

    if by == "email" and send_file and output_paths:
        email_service = get_email_service()
        try:
            asyncio.run(email_service.send(
                project="confirmation",
                function="file_confirmation",
                html_body=html_body,
                env=cmd.get("env", "prod"),
                subject_suffix=cmd.get("trade_date") if cmd.get("trade_date") != "19000101" else None,
                attachments=output_paths,
            ))
        except Exception as exc:
            logger.warning("fc_send_email: email sending failed, retrying: %s", exc)
            raise self.retry(exc=exc)

    _log_step("fc_send_email", pipeline_key, _trace, "completed")
    return {
        "pipeline_key": pipeline_key,
        "step": "send_email",
        "status": "success",
        "output_paths": output_paths,
        "html_body": html_body,
        "success": report_ctx.get("success", True),
    }
