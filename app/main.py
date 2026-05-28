"""
SENTINEL - Self-healing AI orchestration platform.

Main FastAPI application entry point.
Wires together routers, middleware, lifespan events,
streaming infrastructure, and observability services.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import init_db
from app.api.routers import chat
# Future router imports
from app.api.routers.chat import router as chat_router
# from app.api.routers.health import router as health_router
# from app.api.routers.chaos import router as chaos_router
# from app.api.routers.metrics import router as metrics_router

# Future infrastructure services
# from app.core.logging import configure_logging
# from app.streaming.event_bus import EventBus
# from app.streaming.manager import StreamingManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.

    Startup:
    - Initialize database
    - Initialize streaming infrastructure
    - Warm provider pools
    - Restore circuit breaker state
    - Initialize observability services

    Shutdown:
    - Gracefully close async resources
    - Flush pending events/logs
    """

    print("🛡️ SENTINEL starting up...")

    # Initialize database
    await init_db()

    # Future infrastructure initialization
    #
    # app.state.event_bus = EventBus()
    # app.state.streaming_manager = StreamingManager(
    #     bus=app.state.event_bus
    # )
    #
    # configure_logging()

    print("✅ SENTINEL initialized successfully")

    yield

    print("🛑 SENTINEL shutting down...")

    # Future graceful shutdown hooks
    #
    # await app.state.event_bus.close()
    # await app.state.streaming_manager.shutdown()

    print("✅ SENTINEL shutdown complete")


def create_app() -> FastAPI:
    """
    FastAPI application factory.
    """

    app = FastAPI(
        title="SENTINEL",
        description=(
            "Self-healing AI orchestration platform "
            "with intelligent failover and observability"
        ),
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Router registration
    app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
    #
    # Uncomment as modules are implemented.
    #
    # app.include_router(
    #     chat_router,
    #     prefix="/chat",
    #     tags=["chat"],
    # )
    #
    # app.include_router(
    #     health_router,
    #     prefix="/health",
    #     tags=["health"],
    # )
    #
    # app.include_router(
    #     chaos_router,
    #     prefix="/chaos",
    #     tags=["chaos"],
    # )
    #
    # app.include_router(
    #     metrics_router,
    #     prefix="/metrics",
    #     tags=["metrics"],
    # )

    @app.get("/", tags=["system"])
    async def root():
        """
        Root health endpoint.
        """

        return {
            "service": "SENTINEL",
            "status": "online",
            "version": "0.2.0",
            "architecture": "self-healing-ai-orchestration",
            "features": [
                "provider_failover",
                "tool_execution",
                "streaming",
                "observability",
                "resilience",
            ],
        }

    @app.get("/health", tags=["health"])
    async def health_check():
        """
        Lightweight health check endpoint.
        """

        return {
            "status": "healthy",
        }

    return app


app = create_app()