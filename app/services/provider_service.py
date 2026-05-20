import httpx
import time
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ProviderResponse:
    def __init__(self, success: bool, content: Optional[str] = None, error: Optional[str] = None, latency: float = 0.0):
        self.success = success
        self.content = content
        self.error = error
        self.latency = latency

class ProviderService:
    """
    Service to handle communication with AI providers.
    Currently focused on Ollama integration.
    """
    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.api_key = settings.OLLAMA_API_KEY

    async def call_model(self, model_name: str, prompt: str) -> ProviderResponse:
        url = f"{self.host}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=settings.TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                latency = (time.perf_counter() - start_time) * 1000
                return ProviderResponse(
                    success=True, 
                    content=data.get("response"), 
                    latency=latency
                )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            logger.error(f"Provider error for model {model_name}: {str(e)}")
            return ProviderResponse(
                success=False, 
                error=str(e), 
                latency=latency
            )
