from fastapi import APIRouter, HTTPException, Request, Form
import json
from fastapi.responses import RedirectResponse
from app.models.schemas import EmailRequest, EmailResponse, AutoReplyResponse
from app.services.email_processor import email_processor
from app.services.ollama_service import ollama_service
from app.services.gmail_service import gmail_service, SCOPES
from app.services.whatsapp_service import whatsapp_service
from google_auth_oauthlib.flow import Flow
import logging
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

logger = logging.getLogger(__name__)
router = APIRouter()

oauth_state_store = {}

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

@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    logger.info(f"Received WhatsApp from {From}: {Body}")
    req = EmailRequest(
        sender=From,
        subject="WhatsApp Message",
        body=Body,
        context="whatsapp_webhook"
    )
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
        "available_models": ollama_service.available_models,
        "gmail_connected": os.path.exists('token.json'),
        "whatsapp_connected": bool(os.getenv('TWILIO_ACCOUNT_SID'))
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

@router.get("/allowed-senders")
async def get_allowed_senders():
    try:
        if not os.path.exists(email_processor.config_path):
            return {"allowed_emails": []}
        with open(email_processor.config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading allowed senders: {e}")
        return {"allowed_emails": []}

@router.post("/allow-sender")
async def allow_sender(request: Request):
    try:
        data = await request.json()
        email_to_allow = data.get("email", "").lower()
        if not email_to_allow:
            raise HTTPException(status_code=400, detail="Email is required")
        allowed_data = {"allowed_emails": []}
        if os.path.exists(email_processor.config_path):
            with open(email_processor.config_path, 'r') as f:
                allowed_data = json.load(f)
        if email_to_allow not in [e.lower() for e in allowed_data["allowed_emails"]]:
            allowed_data["allowed_emails"].append(email_to_allow)
            with open(email_processor.config_path, 'w') as f:
                json.dump(allowed_data, f, indent=4)
        return {"status": "success", "allowed_emails": allowed_data["allowed_emails"]}
    except Exception as e:
        logger.error(f"Error allowing sender: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve-once")
async def approve_once(request: Request):
    try:
        data = await request.json()
        email = data.get("email", "").lower()
        if not email:
            raise HTTPException(status_code=400, detail="Email is required")
        email_processor.approve_once(email)
        return {"status": "success", "message": f"Sender {email} approved for this session."}
    except Exception as e:
        logger.error(f"Error in approve-once: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/allow-sender")
async def remove_sender(email: str):
    try:
        email_to_remove = email.lower()
        if not os.path.exists(email_processor.config_path):
            return {"status": "success"}
        with open(email_processor.config_path, 'r') as f:
            allowed_data = json.load(f)
        allowed_data["allowed_emails"] = [e for e in allowed_data["allowed_emails"] if e.lower() != email_to_remove]
        with open(email_processor.config_path, 'w') as f:
            json.dump(allowed_data, f, indent=4)
        return {"status": "success", "allowed_emails": allowed_data["allowed_emails"]}
    except Exception as e:
        logger.error(f"Error removing sender: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-info")
async def get_user_info():
    return email_processor.get_user_info()

@router.post("/user-info")
async def update_user_info(request: Request):
    try:
        data = await request.json()
        name = data.get("name")
        email = data.get("email")
        if not name or not email:
            raise HTTPException(status_code=400, detail="Name and Email are required")
        email_processor.save_user_info(name, email)
        return {"status": "success", "user_info": {"name": name, "email": email}}
    except Exception as e:
        logger.error(f"Error updating user info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/gmail/login")
async def gmail_login():
    if not os.path.exists('credentials.json'):
        raise HTTPException(status_code=400, detail="credentials.json not found.")
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/api/v1/auth/gmail/callback'
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    oauth_state_store[state] = flow.code_verifier
    return RedirectResponse(authorization_url)

@router.get("/auth/gmail/callback")
async def gmail_callback(request: Request):
    try:
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        if not code:
            raise HTTPException(status_code=400, detail="Code not provided")
        code_verifier = oauth_state_store.get(state)
        flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES, redirect_uri='http://localhost:8000/api/v1/auth/gmail/callback', state=state)
        flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        creds = flow.credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        gmail_service._authenticate()
        return {"message": "Success! You can close this tab and return to the dashboard."}
    except Exception as e:
        import traceback
        logger.error(f"Gmail Auth Callback Error:\n{traceback.format_exc()}")
        return {"error": str(e)}

@router.get("/gmail/sync")
async def gmail_sync():
    if not gmail_service.creds:
        return {"error": "Gmail not authenticated."}
    unread_emails = gmail_service.fetch_unread_emails(max_results=10)
    results = []
    for email in unread_emails:
        req = EmailRequest(sender=email['sender'], subject=email['subject'], body=email['body'], context="gmail_sync")
        ai_decision = email_processor.auto_reply(req)
        status = "ignored"
        if ai_decision.should_auto_reply:
            success = gmail_service.send_reply(original_email_id=email['id'], thread_id=email['threadId'], reply_text=ai_decision.ai_response)
            status = "replied" if success else "failed_to_reply"
        results.append({
            "id": email['id'], 
            "threadId": email['threadId'],
            "sender": email['sender'], 
            "subject": email['subject'], 
            "classification": ai_decision.classification, 
            "status": status, 
            "reason": ai_decision.reason,
            "timestamp": email.get('timestamp', 0)
        })
    return {"synced": len(unread_emails), "actions": results}

@router.post("/gmail/process-single")
async def process_single(request: Request):
    try:
        data = await request.json()
        email_id = data.get("id")
        thread_id = data.get("threadId")
        if not email_id or not thread_id:
            raise HTTPException(status_code=400, detail="Email ID and Thread ID are required")
        
        # Fetch the email content
        service = gmail_service.get_service()
        txt = service.users().messages().get(userId='me', id=email_id).execute()
        
        # Extract basic info needed for classification/generation
        sender = ""
        subject = ""
        for header in txt['payload']['headers']:
            if header['name'] == 'From': sender = header['value']
            if header['name'] == 'Subject': subject = header['value']
        
        # Simple body extraction logic similar to fetch_unread_emails
        import base64
        payload = txt.get('payload', {})
        parts = payload.get('parts', [])
        if not parts:
            data_body = payload.get('body', {}).get('data', '')
        else:
            data_body = parts[0].get('body', {}).get('data', '')
        
        body = ""
        if data_body:
            body = base64.urlsafe_b64decode(data_body).decode('utf-8')

        req = EmailRequest(sender=sender, subject=subject, body=body, context="manual_process")
        ai_decision = email_processor.auto_reply(req)
        
        if ai_decision.should_auto_reply:
            success = gmail_service.send_reply(original_email_id=email_id, thread_id=thread_id, reply_text=ai_decision.ai_response)
            if success:
                return {"status": "success", "message": "Replied successfully"}
            else:
                return {"status": "error", "message": "Failed to send reply"}
        else:
            return {"status": "error", "message": f"AI still requires human attention: {ai_decision.reason}"}
            
    except Exception as e:
        logger.error(f"Error processing single email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gmail/create-draft")
async def create_draft(request: Request):
    try:
        data = await request.json()
        recipient = data.get("recipient")
        subject = data.get("subject")
        prompt = data.get("prompt")
        if not recipient or not subject or not prompt:
            raise HTTPException(status_code=400, detail="Recipient, Subject, and Prompt are required")
        draft_content = email_processor.create_email(recipient, subject, prompt)
        return {"status": "success", "draft": draft_content}
    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gmail/send-new")
async def send_new_email(request: Request):
    try:
        data = await request.json()
        recipient = data.get("recipient")
        subject = data.get("subject")
        body = data.get("body")
        if not recipient or not subject or not body:
            raise HTTPException(status_code=400, detail="Recipient, Subject, and Body are required")
        success = gmail_service.send_new_email(recipient, subject, body)
        if success:
            return {"status": "success", "message": "Email sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=str(e))