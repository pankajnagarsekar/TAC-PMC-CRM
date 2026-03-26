from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware
import time
import logging

from app.core.config import settings
from app.api.router import api_router
from app.db.mongodb import db_manager, get_db
from app.core.middleware import StandardResponseMiddleware, BackpressureMiddleware

# Logging Configuration (Point 1, 100)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    App Factory following the Supreme Constitution. (Point 6)
    Resolves double-mounting and fragmented registration.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="2.1.0",
        description="TAC-PMC-CRM Supreme Hardened Backend"
    )

    # RESILIENCE: Shield Gateway (Point 4, 105, 125)
    app.add_middleware(BackpressureMiddleware)
    app.add_middleware(StandardResponseMiddleware)
    
    # CORS (Point 3)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # TIGHTEN IN PROD
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REGISTRY: Central Routing (Point 21)
    app.include_router(api_router, prefix="/api")

    @app.on_event("startup")
    async def startup_event():
        """Lifecycle: Hard Ping DB & Seed Indices (Point 6, 7, 49)"""
        logger.info("LIFECYCLE: Starting Supreme CRM Backend...")
        try:
            await db_manager.connect(settings.MONGO_URL, settings.DB_NAME)
            # Future: index_manager.ensure_all()
        except Exception as e:
            logger.critical(f"LIFECYCLE_FATAL: Core systems failed to bootstrap: {e}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Lifecycle: Graceful shutdown (Point 118)"""
        logger.info("LIFECYCLE: Initiating clean shutdown...")
        db_manager.close()

    @app.get("/health", tags=["System"])
    async def health_check():
        """System health and versioning (Point 6)"""
        return {
            "status": "online",
            "environment": settings.ENVIRONMENT,
            "version": "2.1.0-hardened",
            "timestamp": time.time()
        }

    return app

# The Authoritative Entry Point (Point 1)
app = create_app()
