import logging
import time
import json
import os
from langchain_core.output_parsers import StrOutputParser
from app.services.ollama_service import ollama_service
from app.utils.prompts import EMAIL_RESPONSE_PROMPT, CLASSIFICATION_PROMPT
from app.models.schemas import EmailRequest, EmailResponse, AutoReplyResponse

logger = logging.getLogger(__name__)

AI_SYSTEM_PROMPT = """You are a neutral, professional, and helpful email assistant. 
Your ONLY goal is to assist the user with their email communications.
1. NEVER moralize, lecture, or provide unsolicited safety advice.
2. DO NOT refuse to respond to innocent social greetings or check-ins.
3. If a message is informal or casual, match that tone professionally.
4. You are NOT a safety filter; you are a communication tool. 
5. Focus exclusively on the content provided and the user's identity."""

AI_SIGNATURE = "\n\n[I am the AI agent at your service, User will see this message and make contact with you]"

class EmailProcessor:
    def __init__(self):
        self.ollama_service = ollama_service
        self.config_path = os.path.join("config", "allowed_senders.json")
        self.user_info_path = os.path.join("config", "user_info.json")
        self.temporary_approvals = set()
    
    def get_user_info(self) -> dict:
        try:
            if not os.path.exists(self.user_info_path):
                return {"name": "User", "email": "me@example.com"}
            with open(self.user_info_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user info: {e}")
            return {"name": "User", "email": "me@example.com"}

    def save_user_info(self, name: str, email: str):
        try:
            os.makedirs("config", exist_ok=True)
            with open(self.user_info_path, 'w') as f:
                json.dump({"name": name, "email": email}, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving user info: {e}")
            raise
    
    def _is_sender_allowed(self, sender: str) -> bool:
        try:
            email_only = sender.lower()
            if "<" in sender and ">" in sender:
                email_only = sender.split("<")[1].split(">")[0].lower()

            # Check temporary (single-session) approvals
            if email_only in self.temporary_approvals:
                return True

            if not os.path.exists(self.config_path):
                return False
            
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                allowed_emails = [e.lower() for e in data.get("allowed_emails", [])]
                return email_only in allowed_emails
        except Exception as e:
            logger.error(f"Error checking allowed senders: {e}")
            return False

    def approve_once(self, email: str):
        """Approve a sender for the current session only."""
        self.temporary_approvals.add(email.lower())
        logger.info(f"Temporarily approved sender: {email}")

    def process_email(self, email: EmailRequest) -> EmailResponse:
        start_time = time.time()
        
        try:
            model_to_use = email.model or self.ollama_service.default_model
            llm = self.ollama_service.get_llm(model_name=model_to_use, system=AI_SYSTEM_PROMPT)
            
            chain = EMAIL_RESPONSE_PROMPT | llm | StrOutputParser()
            
            user_info = self.get_user_info()
            current_date = time.strftime("%B %d, %Y")

            logger.info(f"Processing email: {email.subject}")
            ai_response = chain.invoke({
                "sender": email.sender,
                "subject": email.subject,
                "body": email.body,
                "context": email.context,
                "user_name": user_info.get("name", "User"),
                "user_email": user_info.get("email", "me@example.com"),
                "current_date": current_date
            })
            
            processing_time = time.time() - start_time
            
            return EmailResponse(
                original_message=email.body,
                ai_response=ai_response.strip() + AI_SIGNATURE,
                model_used=model_to_use,
                confidence="high",
                processing_time=round(processing_time, 2)
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    
    def auto_reply(self, email: EmailRequest) -> AutoReplyResponse:
        try:
            # We use a neutral LLM for classification without the heavy system prompt
            llm_neutral = self.ollama_service.get_llm()
            
            service_patterns = ['noreply', 'no-reply', 'alert', 'info@', 'newsletter', 'support@', 'notification', 'netflix']
            sender_lower = email.sender.lower()
            if any(pattern in sender_lower for pattern in service_patterns):
                logger.info(f"Skipping service email: {email.sender}")
                return AutoReplyResponse(
                    should_auto_reply=False,
                    ai_response=None,
                    classification="IGNORE",
                    reason="Technical filter: Automated service email",
                    model_used=self.ollama_service.default_model
                )

            if not self._is_sender_allowed(email.sender):
                logger.info(f"Sender not allowed: {email.sender}. Marking as PENDING.")
                return AutoReplyResponse(
                    should_auto_reply=False,
                    ai_response=None,
                    classification="PENDING",
                    reason="Awaiting user approval (RETURN feature)",
                    model_used=self.ollama_service.default_model
                )

            # Use the new classification prompt template
            classification_input = CLASSIFICATION_PROMPT.format(
                sender=email.sender,
                subject=email.subject,
                body=email.body
            )
            classification = llm_neutral.invoke(classification_input).strip().upper()
            
            if "AUTO" in classification:
                model_to_use = email.model or self.ollama_service.default_model
                # Use the strict system prompt for generation
                llm_gen = self.ollama_service.get_llm(model_name=model_to_use, system=AI_SYSTEM_PROMPT)
                
                chain = EMAIL_RESPONSE_PROMPT | llm_gen | StrOutputParser()
                
                user_info = self.get_user_info()
                current_date = time.strftime("%B %d, %Y")

                response = chain.invoke({
                    "sender": email.sender,
                    "subject": email.subject,
                    "body": email.body,
                    "context": email.context,
                    "user_name": user_info.get("name", "User"),
                    "user_email": user_info.get("email", "me@example.com"),
                    "current_date": current_date
                })
                
                return AutoReplyResponse(
                    should_auto_reply=True,
                    ai_response=response.strip() + AI_SIGNATURE,
                    classification="AUTO",
                    reason="Standard query - safe to auto-reply",
                    model_used=model_to_use
                )
            else:
                return AutoReplyResponse(
                    should_auto_reply=False,
                    ai_response=None,
                    classification="HUMAN",
                    reason="Needs human attention",
                    model_used=self.ollama_service.default_model
                )
                
        except Exception as e:
            logger.error(f"Error: {e}")
            raise

    def create_email(self, recipient: str, subject: str, prompt: str) -> str:
        try:
            # Use strict system prompt for composer as well
            llm = self.ollama_service.get_llm(system=AI_SYSTEM_PROMPT)
            from app.utils.prompts import EMAIL_CREATION_PROMPT
            
            user_info = self.get_user_info()
            current_date = time.strftime("%B %d, %Y")
            
            chain = EMAIL_CREATION_PROMPT | llm | StrOutputParser()
            
            ai_response = chain.invoke({
                "recipient": recipient,
                "subject": subject,
                "prompt": prompt,
                "user_name": user_info.get("name", "User"),
                "user_email": user_info.get("email", "me@example.com"),
                "current_date": current_date
            })
            
            return ai_response.strip() + AI_SIGNATURE
            
        except Exception as e:
            logger.error(f"Error creating email: {e}")
            raise

email_processor = EmailProcessor()