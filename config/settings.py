from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "AI Mail Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "llama3.1"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Twilio / WhatsApp Settings
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None # e.g., 'whatsapp:+14155238886'

    
    class Config:
        env_file = ".env"

settings = Settings()