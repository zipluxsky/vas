import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import LogManager
from app.reports.file_confirmation.engine import FileConfirmationEngine
from app.schemas.report_models import FileConfirmationInput, ReportGenerationResponse
from app.services.db_service import DatabaseService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


async def run_file_confirmation(
    cmd: FileConfirmationInput,
    host: str = "0.0.0.0",
    db_service: Optional[DatabaseService] = None,
    email_service: Optional[EmailService] = None,
) -> Dict[str, Any]:
    """Run file confirmation report using the full legacy engine.

    Returns {"html": str, "output_paths": list[str], "success": bool}.
    """
    if db_service is None or email_service is None:
        from app.api.deps import get_db_service, get_email_service

        db_service = get_db_service(env=cmd.env)
        email_service = get_email_service()

    log_manager = LogManager("monitor", "fc_%s" % host)

    engine = FileConfirmationEngine(db_service)
    result = engine.generate(cmd, log_manager)

    output_paths = result.get("output_paths", [])
    html_body = result.get("html_body", "")
    log_html = result.get("log_html", "")
    success = result.get("success", False)

    # --- delivery branch (mirrors legacy lines 608-620) ---
    if cmd.by == "download":
        return {
            "html": log_html,
            "output_paths": output_paths,
            "success": success,
        }

    if cmd.send_file and output_paths:
        try:
            await email_service.send(
                project="confirmation",
                function="file_confirmation",
                html_body=html_body,
                env=cmd.env,
                subject_suffix=cmd.trade_date if cmd.trade_date != "19000101" else None,
                attachments=output_paths,
            )
        except Exception as e:
            logger.warning("Report generated but email sending failed: %s", e)
    elif not cmd.send_file:
        _save_email_cache(cmd, host, html_body, output_paths)

    return {
        "html": log_html,
        "output_paths": output_paths,
        "success": success,
    }


def _save_email_cache(
    cmd: FileConfirmationInput,
    host: str,
    str_body: str,
    str_files: list,
) -> None:
    """Persist temp email data for deferred sending (legacy send_file=False path)."""
    cache_dir = os.path.join(str(settings.BASE_DIR.parent), "email_cache")
    os.makedirs(cache_dir, exist_ok=True)

    td = cmd.trade_date if cmd.trade_date != "19000101" else datetime.now().strftime("%Y%m%d")
    temp_data = {
        cmd.cpty: {
            "str_body": str_body,
            "destination": host,
            "env": cmd.env,
            "host": host,
            "s_date": td,
            "str_files": str_files,
        }
    }
    path = os.path.join(cache_dir, f"{cmd.cpty}_{td}_temp_email_data.json")
    with open(path, "w") as f:
        json.dump(temp_data, f)
    logger.info("Saved email cache to %s", path)
