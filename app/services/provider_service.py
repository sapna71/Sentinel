import httpx
import time
import logging
from typing import Optional
from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import Provider
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime

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
        self.host = settings.ollama_base_url
        self.api_key = settings.openai_api_key if hasattr(settings, 'openai_api_key') else ""

    async def get_or_create_provider(self, model_name: str) -> Provider:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Provider).filter_by(model_name=model_name))
            provider = result.scalar_one_or_none()
            if not provider:
                provider = Provider(
                    name=model_name.split(":")[0], 
                    model_name=model_name,
                    is_active=True,
                    is_healthy=True,
                    last_checked=datetime.utcnow()
                )
                session.add(provider)
                await session.commit()
                await session.refresh(provider)
            return provider

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

    async def get_provider(self, provider_id: str) -> ProviderResponse:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Provider).where(Provider.id == provider_id).options(selectinload(Provider.models))
            )
            provider = result.scalar()
            if provider:
                return ProviderResponse(
                    success=True, 
                    content=provider.json(),
                    latency=0.0
                )
            else:
                return ProviderResponse(
                    success=False, 
                    error=f"Provider {provider_id} not found",
                    latency=0.0
                )
