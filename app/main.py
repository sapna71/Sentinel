"""
SENTINEL - Self-healing AI orchestration platform.

Main FastAPI application entry point.
Wires together all routers, middleware, lifespan events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# These imports will be filled in Phase 2+ as modules are built.
# Placeholder structure to validate project layout now.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown logic:
    - Initialize database
    - Warm up provider connections
    - Reset chaos state
    """
    # Phase 2: db init goes here
    # Phase 3: provider health checks go here
    print("🛡️  SENTINEL starting up...")
    yield
    print("🛡️  SENTINEL shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SENTINEL",
        description="Self-healing AI orchestration platform with intelligent failover",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow Next.js frontend in dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers registered in Phase 5
    # app.include_router(chat_router, prefix="/chat", tags=["chat"])
    # app.include_router(chaos_router, prefix="/chaos", tags=["chaos"])
    # app.include_router(health_router, prefix="/health", tags=["health"])
    # app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])

    @app.get("/")
    async def root():
        return {
            "service": "SENTINEL",
            "status": "online",
            "version": "0.1.0",
            "message": "Self-healing AI orchestration platform",
        }

    return app


app = create_app()