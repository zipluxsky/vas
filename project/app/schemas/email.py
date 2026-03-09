from pydantic import BaseModel
from typing import List, Optional

class EmailAddress(BaseModel):
    email: str
    name: Optional[str] = None

class EmailMessage(BaseModel):
    subject: str
    body: str
    to_addresses: List[str]
    cc_addresses: Optional[List[str]] = []
    bcc_addresses: Optional[List[str]] = []
    attachments: Optional[List[str]] = []
    is_html: bool = False
