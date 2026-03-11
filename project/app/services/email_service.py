import smtplib
import logging
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings

logger = logging.getLogger(__name__)

SMTP_HOST = "mailhost"
SMTP_PORT = 25


def _resolve_allowed_attachment_paths(allowed_base: str, paths: Optional[List[str]]) -> List[Path]:
    """
    Resolve paths to real paths and ensure they are under allowed_base (prevents path traversal).
    If allowed_base is empty, no path-based attachments are permitted.
    Raises ValueError if any path is outside the allowed directory.
    """
    if not paths:
        return []
    if not (allowed_base and allowed_base.strip()):
        raise ValueError("Attachment paths are not allowed: ATTACHMENT_ALLOWED_DIR is not set")
    base = Path(allowed_base).resolve()
    if not base.is_dir():
        raise ValueError("ATTACHMENT_ALLOWED_DIR is not a valid directory")
    resolved = []
    for p in paths:
        if not (p and str(p).strip()):
            continue
        path = Path(p).resolve()
        if not path.is_file():
            logger.warning(f"Attachment path is not a file or does not exist: {path}")
            continue
        try:
            path.relative_to(base)
        except ValueError:
            raise ValueError(f"Attachment path not under allowed directory: {p!r}")
        resolved.append(path)
    return resolved


class EmailService:
    def __init__(self, email_config: Dict[str, Any]):
        self.email_config = email_config

        template_dir = settings.BASE_DIR / "app" / "templates" / "email"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def _send_smtp(self, msg: MIMEMultipart) -> bool:
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return False

    def _attach_files(self, msg: MIMEMultipart, paths: List[Path]):
        for path in paths:
            part = MIMEBase("application", "octet-stream")
            with open(path, "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={path.name}")
            msg.attach(part)

    def _lookup_email_config(self, project: str, function: str) -> Dict[str, Any]:
        """Look up email routing config by project (domain_name) and function (scenario_name)."""
        domain = self.email_config.get(project, {})
        scenario = domain.get(function, {})
        return scenario.get("email", {})

    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        template_name: str,
        context: dict,
        attachment_paths: List[str] = None,
        send_from: str = None,
        cc_addresses: List[str] = None,
    ) -> bool:
        try:
            template = self.env.get_template(template_name)
            html_content = template.render(context)

            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = send_from or "noreply@vasi.com"
            msg["To"] = ", ".join(to_addresses)
            if cc_addresses:
                msg["Cc"] = ", ".join(cc_addresses)
            msg.attach(MIMEText(html_content, "html"))

            if attachment_paths:
                allowed = _resolve_allowed_attachment_paths(
                    settings.ATTACHMENT_ALLOWED_DIR, attachment_paths
                )
                self._attach_files(msg, allowed)

            all_recipients = list(to_addresses) + (cc_addresses or [])
            return self._send_smtp(msg)
        except Exception as e:
            logger.error(f"Failed to send email to {to_addresses}: {e}")
            return False

    def send_report(
        self,
        report_name: str,
        file_paths: List[str],
        target_date: datetime,
        project: str = "",
        function: str = "",
        env: Optional[str] = None,
    ) -> bool:
        """Send report email with attachments. Looks up recipients from email_config matrix."""
        cfg = self._lookup_email_config(project or report_name, function or report_name)
        env_key = env or settings.ENVIRONMENT

        send_from = cfg.get("send_from", "noreply@vasi.com")
        to_addresses = cfg.get("to_addresses", {}).get(env_key, [])
        cc_addresses = cfg.get("cc_addresses", {}).get(env_key, [])

        if not to_addresses:
            logger.warning(f"No to_addresses found for report={report_name}, env={env_key}; skipping send")
            return False

        date_str = target_date.strftime("%Y-%m-%d")
        subject = cfg.get("subject", f"Automated Report: {report_name}") + f" - {date_str}"
        context = {
            "report_name": report_name,
            "date_str": date_str,
            "message": f"Please find attached the {report_name} report for {date_str}.",
        }
        return self.send_email(
            to_addresses=to_addresses,
            subject=subject,
            template_name="report_email.html",
            context=context,
            attachment_paths=file_paths,
            send_from=send_from,
            cc_addresses=cc_addresses,
        )

    async def send(
        self,
        project: str,
        function: str,
        html_body: str = "",
        env: Optional[str] = None,
        subject_suffix: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> None:
        """Send email using matrix configuration (project/function/env). Used by POST /communicators/email_sender."""
        cfg = self._lookup_email_config(project, function)
        if not cfg:
            logger.warning(f"No email config found for project={project}, function={function}")
            return

        env_key = env or settings.ENVIRONMENT
        to_addresses = cfg.get("to_addresses", {}).get(env_key, [])
        cc_addresses = cfg.get("cc_addresses", {}).get(env_key, [])
        send_from = cfg.get("send_from", "noreply@vasi.com")

        subject = cfg.get("subject", f"{project} / {function}")
        if subject_suffix:
            subject = f"{subject} {subject_suffix}"

        body = html_body or cfg.get("message", "(no body)")

        def _do_send():
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = send_from
            msg["To"] = ", ".join(to_addresses)
            if cc_addresses:
                msg["Cc"] = ", ".join(cc_addresses)
            msg.attach(MIMEText(body, "html"))

            if attachments:
                allowed_paths = _resolve_allowed_attachment_paths(
                    settings.ATTACHMENT_ALLOWED_DIR, attachments
                )
                self._attach_files(msg, allowed_paths)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.send_message(msg)

        await asyncio.to_thread(_do_send)
