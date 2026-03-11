import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app.services.db_service import DatabaseService
from app.services.email_service import EmailService
from app.reports.file_confirmation.engine import FileConfirmationEngine
from app.schemas.report_models import ReportGenerationResponse, FileConfirmationInput

logger = logging.getLogger(__name__)


def _parse_trade_date(trade_date: str) -> datetime:
    """Parse trade_date (YYYYMMDD) to datetime. Returns today if invalid or default."""
    if not trade_date or trade_date == "19000101":
        return datetime.now()
    try:
        return datetime.strptime(trade_date.strip(), "%Y%m%d")
    except ValueError:
        return datetime.now()


async def run_file_confirmation(
    cmd: FileConfirmationInput,
    host: str = "0.0.0.0",
    db_service: Optional[DatabaseService] = None,
    email_service: Optional[EmailService] = None,
) -> str:
    """
    Run file confirmation report and return HTML result.
    Used by GET /front_office/file_confirmation and CLI file-confirmation.
    """
    if db_service is None or email_service is None:
        from app.api.deps import get_db_service, get_email_service
        db_service = get_db_service()
        email_service = get_email_service()
    target_dt = _parse_trade_date(cmd.trade_date)
    result = await generate_file_confirmation_report(
        db_service=db_service,
        email_service=email_service,
        cmd=cmd,
        target_date=target_dt,
    )
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>File Confirmation Report</title></head><body>",
        "<h1>File Confirmation Report</h1>",
        f"<p><strong>Success:</strong> {result.success}</p>",
        f"<p><strong>Message:</strong> {result.message}</p>",
        f"<p><strong>Record count:</strong> {result.record_count}</p>",
    ]
    if result.output_paths:
        html_parts.append("<p><strong>Output paths:</strong></p><ul>")
        for p in result.output_paths:
            html_parts.append(f"<li>{p}</li>")
        html_parts.append("</ul>")
    html_parts.append("</body></html>")
    return "".join(html_parts)


async def generate_file_confirmation_report(
    db_service: DatabaseService,
    email_service: EmailService,
    cmd: FileConfirmationInput,
    target_date: Optional[datetime] = None,
) -> ReportGenerationResponse:
    """Generate and distribute the file confirmation report. Uses cmd.cpty, cmd.by, cmd.send_file for engine/email."""
    if target_date is None:
        target_date = datetime.now()

    logger.info(f"Initiating file confirmation report for {target_date.date()} (cpty={cmd.cpty}, by={cmd.by}, env={cmd.env})")

    try:
        # File confirmation uses inline defaults; no external config file.
        config = {"formats": ["csv"], "formatting": {}}
        overrides = {"cpty": cmd.cpty, "env": cmd.env}

        # Initialize engine and generate with overrides
        engine = FileConfirmationEngine(db_service, config)
        result = engine.generate(target_date, overrides=overrides)

        if not result.get("success"):
            return ReportGenerationResponse(
                success=False,
                message=f"Generation failed: {result.get('error')}"
            )

        # Send via email only when send_file=True and by=email
        output_paths = result.get("output_paths", [])
        if output_paths and cmd.send_file and cmd.by == "email":
            email_sent = email_service.send_report(
                "File Confirmation",
                output_paths,
                target_date
            )
            if not email_sent:
                logger.warning("Report generated but email sending failed")
                
        return ReportGenerationResponse(
            success=True,
            message="Report generated successfully",
            output_paths=output_paths,
            record_count=result.get("record_count", 0)
        )
        
    except Exception as e:
        logger.error(f"Unhandled error in report generation: {e}")
        return ReportGenerationResponse(
            success=False,
            message=str(e)
        )
