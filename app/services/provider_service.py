import time
import logging
from typing import Optional
from datetime import datetime

import httpx
from google import genai
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import Provider


logger = logging.getLogger(__name__)


class ProviderResponse:
    def __init__(
        self,
        success: bool,
        content: Optional[str] = None,
        error: Optional[str] = None,
        latency: float = 0.0,
    ):
        self.success = success
        self.content = content
        self.error = error
        self.latency = latency


class ProviderService:
    """
    Handles communication with Sentinel's AI providers.

    Primary:
        Google Gemini

    Fallback:
        Groq
    """

    def __init__(self):

        # -----------------------------
        # Gemini
        # -----------------------------

        self.gemini_client = None

        if settings.GEMINI_API_KEY:
            self.gemini_client = genai.Client(
                api_key=settings.GEMINI_API_KEY
            )

        # -----------------------------
        # Groq
        # -----------------------------

        self.groq_api_key = settings.GROQ_API_KEY

        self.groq_url = (
            "https://api.groq.com/openai/v1/chat/completions"
        )

    async def get_or_create_provider(
        self,
        model_name: str
    ) -> Provider:

        async with AsyncSessionLocal() as session:

            result = await session.execute(
                select(Provider).filter_by(
                    model_name=model_name
                )
            )

            provider = result.scalar_one_or_none()

            if not provider:

                provider_name = (
                    "groq"
                    if model_name.startswith("openai/")
                    else "gemini"
                )

                provider = Provider(
                    name=provider_name,
                    model_name=model_name,
                    is_active=True,
                    is_healthy=True,
                    last_checked=datetime.utcnow(),
                )

                session.add(provider)

                await session.commit()

                await session.refresh(provider)

            return provider

    async def call_model(
        self,
        model_name: str,
        prompt: str
    ) -> ProviderResponse:

        # Groq models use the openai/ prefix
        if model_name.startswith("openai/"):
            return await self._call_groq(
                model_name,
                prompt
            )

        # Everything else currently goes to Gemini
        return await self._call_gemini(
            model_name,
            prompt
        )

    async def _call_gemini(
        self,
        model_name: str,
        prompt: str
    ) -> ProviderResponse:

        start_time = time.perf_counter()

        try:

            if not self.gemini_client:

                return ProviderResponse(
                    success=False,
                    error="GEMINI_API_KEY is not configured",
                    latency=(
                        time.perf_counter()
                        - start_time
                    ) * 1000,
                )

            logger.info(
                f"Calling Gemini model: {model_name}"
            )

            response = (
                self.gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
            )

            latency = (
                time.perf_counter()
                - start_time
            ) * 1000

            content = response.text

            logger.info(
                f"Gemini request successful: "
                f"model={model_name}, "
                f"latency={latency:.2f}ms"
            )

            return ProviderResponse(
                success=True,
                content=content,
                latency=latency,
            )

        except Exception as e:

            latency = (
                time.perf_counter()
                - start_time
            ) * 1000

            logger.error(
                f"Gemini provider error for "
                f"{model_name}: {str(e)}"
            )

            return ProviderResponse(
                success=False,
                error=str(e),
                latency=latency,
            )

    async def _call_groq(
        self,
        model_name: str,
        prompt: str
    ) -> ProviderResponse:

        start_time = time.perf_counter()

        try:

            if not self.groq_api_key:

                return ProviderResponse(
                    success=False,
                    error="GROQ_API_KEY is not configured",
                    latency=(
                        time.perf_counter()
                        - start_time
                    ) * 1000,
                )

            logger.info(
                f"Calling Groq model: {model_name}"
            )

            headers = {
                "Authorization": (
                    f"Bearer {self.groq_api_key}"
                ),
                "Content-Type": "application/json",
            }

            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "temperature": 0.2,
            }

            async with httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT
            ) as client:

                response = await client.post(
                    self.groq_url,
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

            content = (
                data["choices"][0]
                ["message"]
                ["content"]
            )

            latency = (
                time.perf_counter()
                - start_time
            ) * 1000

            logger.info(
                f"Groq request successful: "
                f"model={model_name}, "
                f"latency={latency:.2f}ms"
            )

            return ProviderResponse(
                success=True,
                content=content,
                latency=latency,
            )

        except Exception as e:

            latency = (
                time.perf_counter()
                - start_time
            ) * 1000

            logger.error(
                f"Groq provider error for "
                f"{model_name}: {str(e)}"
            )

            return ProviderResponse(
                success=False,
                error=str(e),
                latency=latency,
            )

    async def get_provider(
        self,
        provider_id: str
    ) -> ProviderResponse:

        async with AsyncSessionLocal() as session:

            result = await session.execute(
                select(Provider)
                .where(
                    Provider.id == provider_id
                )
                .options(
                    selectinload(
                        Provider.models
                    )
                )
            )

            provider = result.scalar()

            if provider:

                return ProviderResponse(
                    success=True,
                    content=provider.json(),
                    latency=0.0,
                )

            return ProviderResponse(
                success=False,
                error=(
                    f"Provider "
                    f"{provider_id} not found"
                ),
                latency=0.0,
            )