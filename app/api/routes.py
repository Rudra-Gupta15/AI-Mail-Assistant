from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from app.models.schemas import EmailRequest, EmailResponse, AutoReplyResponse
from app.services.email_processor import email_processor
from app.services.ollama_service import ollama_service
from app.services.gmail_service import gmail_service, SCOPES
from app.services.whatsapp_service import whatsapp_service
from google_auth_oauthlib.flow import Flow
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
def root():
    return {
        "message": "🤖 AI Mail Assistant",
        "status": "running",
        "endpoints": {
            "GET /health": "Check health",
            "GET /models": "List models",
            "POST /process-email": "Process email",
            "POST /auto-reply": "Auto-reply decision",
            "GET /auth/gmail/login": "Login to Gmail",
            "GET /gmail/sync": "Sync unread emails",
            "POST /webhooks/whatsapp": "Twilio WhatsApp Webhook"
        }
    }

# ... (other routes remain the same)

@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    """Webhook for receiving WhatsApp messages from Twilio."""
    logger.info(f"Received WhatsApp from {From}: {Body}")
    
    # Create request model
    req = EmailRequest(
        sender=From,
        subject="WhatsApp Message",
        body=Body,
        context="whatsapp_webhook"
    )
    
    # Process using AI
    ai_decision = email_processor.auto_reply(req)
    
    if ai_decision.should_auto_reply:
        success = whatsapp_service.send_message(
            to_number=From,
            message_body=ai_decision.ai_response
        )
        if success:
            return {"status": "replied", "response": ai_decision.ai_response}
        else:
            return {"status": "failed_to_reply"}
            
    return {"status": "human_attention_needed", "classification": ai_decision.classification}


@router.get("/health")
def health_check():
    test = ollama_service.test_connection()
    return {
        "status": "healthy" if test["status"] == "connected" else "unhealthy",
        "ollama": test["status"],
        "model": ollama_service.default_model,
        "available_models": ollama_service.available_models
    }

@router.get("/models")
def list_models():
    return {
        "available_models": ollama_service.available_models,
        "default": ollama_service.default_model
    }

@router.post("/process-email", response_model=EmailResponse)
async def process_email(email: EmailRequest):
    try:
        return email_processor.process_email(email)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auto-reply", response_model=AutoReplyResponse)
async def auto_reply(email: EmailRequest):
    try:
        return email_processor.auto_reply(email)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Gmail OAuth Routes ---

@router.get("/auth/gmail/login")
async def gmail_login():
    if not os.path.exists('credentials.json'):
        raise HTTPException(status_code=400, detail="credentials.json not found. Please upload it to the project root.")
    
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/api/v1/auth/gmail/callback'
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return RedirectResponse(authorization_url)

@router.get("/auth/gmail/callback")
async def gmail_callback(request: Request):
    code = request.query_params.get('code')
    if not code:
        raise HTTPException(status_code=400, detail="Code not provided")
    
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/api/v1/auth/gmail/callback'
    )
    
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    # Re-init the service with new tokens
    gmail_service._authenticate()
    
    return {"message": "Gmail authentication successful! token.json has been created."}

@router.get("/gmail/sync")
async def gmail_sync():
    if not gmail_service.creds:
        return {"error": "Gmail not authenticated. Visit /api/v1/auth/gmail/login first."}
    
    unread_emails = gmail_service.fetch_unread_emails(max_results=5)
    results = []
    
    for email in unread_emails:
        # Create EmailRequest model
        req = EmailRequest(
            sender=email['sender'],
            subject=email['subject'],
            body=email['body'],
            context="gmail_sync"
        )
        
        # Process using AI
        ai_decision = email_processor.auto_reply(req)
        
        status = "ignored"
        if ai_decision.should_auto_reply:
            success = gmail_service.send_reply(
                original_email_id=email['id'],
                thread_id=email['threadId'],
                reply_text=ai_decision.ai_response
            )
            status = "replied" if success else "failed_to_reply"
        
        results.append({
            "id": email['id'],
            "subject": email['subject'],
            "classification": ai_decision.classification,
            "status": status
        })
    
    return {
        "synced": len(unread_emails),
        "actions": results
    }