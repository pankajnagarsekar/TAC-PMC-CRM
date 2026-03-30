import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.lifecycle import BackgroundGuardian
from app.core.middleware import BackpressureMiddleware, StandardResponseMiddleware
from app.db.mongodb import db_manager
from app.modules.shared.domain.exceptions import DomainError

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    App Factory following the Supreme Constitution.
    Handles lifecycle, registry, shielding, and background loops.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="2.2.0+",
        description="TAC-PMC-CRM Supreme Hardened Backend",
    )

    # RESILIENCE: Shield Gateway
    app.add_middleware(BackpressureMiddleware)
    app.add_middleware(StandardResponseMiddleware)

    # CORS (Fixed CR-06: Using restricted list from settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REGISTRY: Central Routing
    app.include_router(api_router, prefix="/api")

    # ERROR HANDLING: Domain → HTTP (Strict Layer Separation)
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        from app.modules.shared.domain.exceptions import (
            AuthenticationError,
            NotFoundError,
            PermissionDeniedError,
        )

        status_code = 400
        if isinstance(exc, NotFoundError):
            status_code = 404
        elif isinstance(exc, PermissionDeniedError):
            status_code = 403
        elif isinstance(exc, AuthenticationError):
            status_code = 401

        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "message": str(exc),
                "entity_id": getattr(exc, "entity_id", "none"),
                "error_type": exc.__class__.__name__,
            },
        )

    # State for background tasks
    state = {"guardian": None}

    @app.on_event("startup")
    async def startup_event():
        """Lifecycle: Hard Ping DB & Boot Guardian (Point 6, 7, 103)"""
        logger.info("LIFECYCLE: Starting Supreme CRM Backend...")
        try:
            await db_manager.connect(settings.MONGO_URL, settings.DB_NAME)

            # Start Background Guardian (Point 103, 122)
            state["guardian"] = BackgroundGuardian(db_manager.get_db())
            await state["guardian"].start()

            if settings.OPENAI_API_KEY:
                logger.info("LIFECYCLE: AI engine active (key detected)")
            else:
                logger.warning("LIFECYCLE: AI engine in MOCK mode (key missing)")

        except Exception as e:
            logger.critical(f"LIFECYCLE_FATAL: Core systems failed to bootstrap: {e}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Lifecycle: Graceful shutdown (Point 118)"""
        logger.info("LIFECYCLE: Initiating clean shutdown...")
        if state["guardian"]:
            await state["guardian"].stop()
        db_manager.close()

    @app.get("/system/health", tags=["System"])
    async def health_check():
        return {
            "status": "online",
            "environment": settings.ENVIRONMENT,
            "version": "2.2.0-hardened",
            "timestamp": time.time(),
        }

    return app


# The Authoritative Entry Point
app = create_app()
