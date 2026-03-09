import os
import logging
from typing import List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from exchangelib import DELEGATE, Account, Credentials, Configuration, Message, Mailbox, HTMLBody, FileAttachment

from app.core.config import settings

logger = logging.getLogger(__name__)

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
                for attachment_path in attachment_paths:
                    if attachment_path and os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            content = f.read()
                        
                        attachment = FileAttachment(
                            name=os.path.basename(attachment_path),
                            content=content
                        )
                        m.attach(attachment)
                    else:
                        logger.warning(f"Attachment not found: {attachment_path}")
    
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