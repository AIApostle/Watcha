"""
Watcha — FastAPI Application Entry Point.

Configures the FastAPI app with CORS, lifespan management,
and mounts all API routers.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)
KEEP_ALIVE_INTERVAL_SECONDS = 14 * 60 + 59


async def _keep_render_alive(service_url: str) -> None:
    """Ping the deployed service before Render's inactivity window elapses."""
    health_url = f"{service_url.rstrip('/')}/api/health"
    timeout = httpx.Timeout(20.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            await asyncio.sleep(KEEP_ALIVE_INTERVAL_SECONDS)
            try:
                response = await client.get(health_url)
                response.raise_for_status()
                logger.info("Render keep-alive ping succeeded.")
            except (httpx.HTTPError, OSError) as exc:
                logger.warning("Render keep-alive ping failed: %s", exc)


# ── Lazy imports for routers (avoids circular imports at module load) ─────────


def _register_routers(app: FastAPI) -> None:
    """Import and register all API routers."""
    from app.auth.router import router as auth_router
    from app.settings.router import router as settings_router
    from app.dashboard.router import router as dashboard_router
    from app.agent.router import router as agent_router

    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])
    app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
    app.include_router(agent_router, prefix="/api/agent", tags=["Agent"])


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🚀 Watcha starting up…")
    keep_alive_task = asyncio.create_task(
        _keep_render_alive(get_settings().render_service_url)
    )
    # Agent worker auto-start could go here in the future
    try:
        yield
    finally:
        keep_alive_task.cancel()
        await asyncio.gather(keep_alive_task, return_exceptions=True)
        logger.info("🛑 Watcha shutting down…")
        # Cleanup: stop APScheduler if running
        from app.agent.worker import agent_worker

        if agent_worker.is_running:
            await agent_worker.stop()
            logger.info("Agent worker stopped.")


# ── App Factory ──────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered market intelligence agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    _register_routers(app)

    # Health check
    @app.get("/api/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": settings.app_name}

    return app


# ── Module-level app instance (for uvicorn) ──────────────────────────────────

app = create_app()
