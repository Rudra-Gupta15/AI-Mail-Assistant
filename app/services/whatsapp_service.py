import logging
from twilio.rest import Client
from config.settings import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_NUMBER
        self.client = None
        
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized.")
            except Exception as e:
                logger.error(f"Error initializing Twilio: {e}")

    def send_message(self, to_number: str, message_body: str):
        """Sends a WhatsApp message via Twilio."""
        if not self.client:
            logger.error("Twilio client not initialized. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")
            return False
            
        if not self.from_number:
            logger.error("TWILIO_WHATSAPP_NUMBER not set.")
            return False

        try:
            # Ensure number is in 'whatsapp:+...' format
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
                
            logger.info(f"Sending WhatsApp message to {to_number}")
            message = self.client.messages.create(
                from_=self.from_number,
                body=message_body,
                to=to_number
            )
            logger.info(f"Message sent successfully. SID: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False

whatsapp_service = WhatsAppService()
