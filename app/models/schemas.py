from pydantic import BaseModel
from typing import Optional

class EmailRequest(BaseModel):
    sender: str
    subject: str
    body: str
    context: str = "general"
    model: Optional[str] = None

class EmailResponse(BaseModel):
    original_message: str
    ai_response: str
    model_used: str
    confidence: str
    processing_time: Optional[float] = None

class AutoReplyResponse(BaseModel):
    should_auto_reply: bool
    ai_response: Optional[str]
    classification: str
    reason: str
    model_used: str