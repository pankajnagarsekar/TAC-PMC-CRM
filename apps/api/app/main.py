import logging
import time
import bcrypt

# Resolve passlib compatibility issue with bcrypt 4.0+
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (), {"__version__": bcrypt.__version__})

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.concurrency import concurrency_hub
from app.core.lifecycle import BackgroundGuardian
from app.core.middleware import BackpressureMiddleware, StandardResponseMiddleware
from app.db.mongodb import db_manager

from app.core.lifecycle import register_exception_handlers

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    App Factory following the Supreme Constitution.
    Handles lifecycle, registry, shielding, and background loops.
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifecycle: Hard Ping DB & Boot Guardian (Point 6, 7, 103)"""
        logger.info("LIFECYCLE: Starting Supreme CRM Backend...")
        try:
            await db_manager.connect(settings.MONGO_URL, settings.DB_NAME)

            # Start Background Guardian (Point 103, 122)
            guardian = BackgroundGuardian(db_manager.get_db())
            await guardian.start()

            if settings.OPENAI_API_KEY:
                logger.info("LIFECYCLE: AI engine active (key detected)")
            else:
                logger.warning("LIFECYCLE: AI engine in MOCK mode (key missing)")

            yield
        except Exception as e:
            logger.critical(f"LIFECYCLE_FATAL: Core systems failed: {e}")
            raise
        finally:
            # Shutdown (Guaranteed even if yield raises or exception occurs)
            logger.info("LIFECYCLE: Initiating clean shutdown...")
            try:
                # We use a try/except for each component to ensure one failure doesn't block others
                if 'guardian' in locals():
                    await guardian.stop()

                # Shutdown concurrency pools
                concurrency_hub.shutdown()

                # Close DB connection
                db_manager.close()
                logger.info("LIFECYCLE: Shutdown complete.")
            except Exception as se:
                logger.error(f"LIFECYCLE_ERROR: Error during shutdown sequence: {se}")

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="2.2.0+",
        description="TAC-PMC-CRM Supreme Hardened Backend",
        lifespan=lifespan,
    )

    # 1. Register Exception Handlers (BUG-10)
    register_exception_handlers(app)

    # 2. Add Middlewares (Point 4, 15, 105)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BackpressureMiddleware)
    app.add_middleware(StandardResponseMiddleware)

    # 3. Include Routers (Point 2)
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/system/health", tags=["System"])
    async def health_check():
        db = db_manager.get_db()
        db_healthy = await BackgroundGuardian.mongodb_health_check(db)

        if not db_healthy:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "degraded",
                    "db": "disconnected",
                    "environment": settings.ENVIRONMENT,
                },
            )

        return {
            "status": "online",
            "db": "connected",
            "environment": settings.ENVIRONMENT,
            "version": "2.2.0-hardened",
            "timestamp": time.time(),
        }

    return app


# The Authoritative Entry Point
app = create_app()
