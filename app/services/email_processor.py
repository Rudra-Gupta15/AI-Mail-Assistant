import logging
import time
from langchain_core.output_parsers import StrOutputParser
from app.services.ollama_service import ollama_service
from app.utils.prompts import EMAIL_RESPONSE_PROMPT, CLASSIFICATION_PROMPT
from app.models.schemas import EmailRequest, EmailResponse, AutoReplyResponse

logger = logging.getLogger(__name__)

class EmailProcessor:
    def __init__(self):
        self.ollama_service = ollama_service
    
    def process_email(self, email: EmailRequest) -> EmailResponse:
        start_time = time.time()
        
        try:
            model_to_use = email.model or self.ollama_service.default_model
            llm = self.ollama_service.get_llm(model_to_use)
            
            # Modern LCEL Chain: prompt | llm | output_parser
            chain = EMAIL_RESPONSE_PROMPT | llm | StrOutputParser()
            
            logger.info(f"Processing email: {email.subject}")
            ai_response = chain.invoke({
                "sender": email.sender,
                "subject": email.subject,
                "body": email.body,
                "context": email.context
            })
            
            processing_time = time.time() - start_time
            
            return EmailResponse(
                original_message=email.body,
                ai_response=ai_response.strip(),
                model_used=model_to_use,
                confidence="high",
                processing_time=round(processing_time, 2)
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
    
    def auto_reply(self, email: EmailRequest) -> AutoReplyResponse:
        try:
            llm = self.ollama_service.get_llm()
            
            # Use simple invoke for classification
            classification_text = CLASSIFICATION_PROMPT.format(
                subject=email.subject,
                body=email.body
            )
            classification = llm.invoke(classification_text).strip().upper()
            
            if "AUTO" in classification:
                model_to_use = email.model or self.ollama_service.default_model
                llm = self.ollama_service.get_llm(model_to_use)
                
                # Modern LCEL Chain
                chain = EMAIL_RESPONSE_PROMPT | llm | StrOutputParser()
                
                response = chain.invoke({
                    "sender": email.sender,
                    "subject": email.subject,
                    "body": email.body,
                    "context": email.context
                })
                
                return AutoReplyResponse(
                    should_auto_reply=True,
                    ai_response=response.strip(),
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

email_processor = EmailProcessor()