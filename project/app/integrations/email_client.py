import smtplib
import imaplib
import email
from email.message import EmailMessage
import logging
from typing import Dict, Any, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class EmailClient:
    """Client for sending and receiving emails"""
    
    def __init__(self, config: Dict[str, Any]):
        self.imap_config = config.get("imap", {})
        self.smtp_config = config.get("smtp", {})
        self.processing_config = config.get("processing", {})
        
    def connect(self) -> bool:
        """Test both IMAP and SMTP connections"""
        try:
            # We don't keep connections open, just test them
            imap_ok = self._test_imap()
            smtp_ok = self._test_smtp()
            return imap_ok and smtp_ok
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False
            
    def _test_imap(self) -> bool:
        """Test IMAP connection"""
        try:
            if self.imap_config.get("use_ssl", True):
                mail = imaplib.IMAP4_SSL(
                    self.imap_config.get("server"),
                    self.imap_config.get("port", 993)
                )
            else:
                mail = imaplib.IMAP4(
                    self.imap_config.get("server"),
                    self.imap_config.get("port", 143)
                )
            mail.login(
                self.imap_config.get("username"),
                self.imap_config.get("password")
            )
            mail.logout()
            return True
        except Exception as e:
            logger.error(f"IMAP test failed: {e}")
            return False
            
    def _test_smtp(self) -> bool:
        """Test SMTP connection"""
        try:
            server = smtplib.SMTP(
                self.smtp_config.get("server"),
                self.smtp_config.get("port", 587)
            )
            if self.smtp_config.get("use_tls", True):
                server.starttls()
            server.login(
                self.smtp_config.get("username"),
                self.smtp_config.get("password")
            )
            server.quit()
            return True
        except Exception as e:
            logger.error(f"SMTP test failed: {e}")
            return False
            
    def send_email(self, subject: str, body: str, to_addresses: List[str], 
                   attachments: List[str] = None) -> bool:
        """Send an email with optional attachments"""
        # Implementation details omitted for brevity
        logger.info(f"Sending email '{subject}' to {to_addresses}")
        return True
