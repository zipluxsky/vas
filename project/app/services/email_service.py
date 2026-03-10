import os
import logging
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from exchangelib import DELEGATE, Account, Credentials, Configuration, Message, Mailbox, HTMLBody, FileAttachment

from app.core.config import settings

logger = logging.getLogger(__name__)


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
        try:
            path = path.resolve()
        except (OSError, RuntimeError):
            raise ValueError(f"Invalid attachment path: {p!r}")
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
    def __init__(self, username, password, email, server="mail.vasi.com"):
        self.username = username
        self.password = password
        self.email = email
        self.server = server
        
        # Save config for fallback behavior mimicking the old client config setup if needed
        self.smtp_config = {"default_recipient": "admin@example.com"}
        
        self.credentials = Credentials(username, password)
        self.config = Configuration(server=server, credentials=self.credentials)
        self.account = Account(
            primary_smtp_address=email,
            config=self.config,
            autodiscover=False,
            access_type=DELEGATE
        )

        template_dir = settings.BASE_DIR / "app" / "templates" / "email"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def _get_account(self):
        return self.account

    def send_email(self, to_addresses: List[str], subject: str, template_name: str, context: dict, attachment_paths: List[str] = None):
        try:
            template = self.env.get_template(template_name)
            html_content = template.render(context)
    
            m = Message(
                account=self.account,
                folder=self.account.sent,
                subject=subject,
                body=HTMLBody(html_content),
                to_recipients=[Mailbox(email_address=addr) for addr in to_addresses]
            )
    
            if attachment_paths:
                allowed = _resolve_allowed_attachment_paths(
                    settings.ATTACHMENT_ALLOWED_DIR, attachment_paths
                )
                for attachment_path in allowed:
                    with open(attachment_path, 'rb') as f:
                        content = f.read()
                    attachment = FileAttachment(
                        name=attachment_path.name,
                        content=content
                    )
                    m.attach(attachment)
    
            m.send_and_save()
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_addresses}: {e}")
            return False

    def send_report(self, report_name: str, file_paths: List[str], target_date: datetime) -> bool:
        """Wrapper method to maintain compatibility with existing Usecases"""
        date_str = target_date.strftime("%Y-%m-%d")
        subject = f"Automated Report: {report_name} - {date_str}"
        
        # For this generic wrapper, we'll try to use a basic template or fallback to a hardcoded html
        # Depending on if a specific report template exists, we can pass context.
        # Assume there's a generic template 'report_email.html' or similar. 
        # If the template doesn't exist, jinja will throw an error, which send_email will catch.
        # But for safety, you should ensure a generic template exists in the directory.
        context = {
            "report_name": report_name,
            "date_str": date_str,
            "message": f"Please find attached the {report_name} report for {date_str}."
        }
        
        # Use default recipient from config or define logic to lookup based on report type
        to_address = self.smtp_config.get("default_recipient", "admin@example.com")
        
        # We assume a template 'report_email.html' might be created. 
        # For now, it will look for it.
        return self.send_email(
            to_addresses=[to_address],
            subject=subject,
            template_name="report_email.html", 
            context=context,
            attachment_paths=file_paths
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
        subject = f"{project} / {function}"
        if subject_suffix:
            subject = f"{subject} {subject_suffix}"
        to_address = self.smtp_config.get("default_recipient", "admin@example.com")
        context = {"body": html_body, "project": project, "function": function}
        # Use raw html_body if no template; send_email uses template. So we need a small inline send.
        def _do_send():
            m = Message(
                account=self.account,
                folder=self.account.sent,
                subject=subject,
                body=HTMLBody(html_body or "(no body)"),
                to_recipients=[Mailbox(email_address=to_address)],
            )
            if attachments:
                allowed_paths = _resolve_allowed_attachment_paths(
                    settings.ATTACHMENT_ALLOWED_DIR, attachments
                )
                for path in allowed_paths:
                    with open(path, "rb") as f:
                        m.attach(FileAttachment(name=path.name, content=f.read()))
            m.send_and_save()

        await asyncio.to_thread(_do_send)