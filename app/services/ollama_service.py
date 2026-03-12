import subprocess
import logging
from typing import List
from langchain_ollama import OllamaLLM as Ollama
from config.settings import settings

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.default_model = settings.DEFAULT_MODEL
        self.available_models = self.get_available_models()
        logger.info(f"Initialized with model: {self.default_model}")
    
    def get_available_models(self) -> List[str]:
        try:
            result = subprocess.run(
                ['ollama', 'list'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            lines = result.stdout.strip().split('\n')[1:]
            models = [line.split()[0] for line in lines if line]
            logger.info(f"Found models: {models}")
            return models
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return [self.default_model]
    
    def get_llm(self, model_name: str = None, system: str = None):
        model = model_name if model_name in self.available_models else self.default_model
        # Inject system prompt via model parameters
        return Ollama(
            model=model, 
            base_url=self.base_url,
            system=system
        )
    
    def test_connection(self) -> dict:
        try:
            llm = self.get_llm()
            response = llm.invoke("Hi")
            return {
                "status": "connected",
                "model": self.default_model,
                "test": response[:30]
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "error": str(e)
            }

ollama_service = OllamaService()