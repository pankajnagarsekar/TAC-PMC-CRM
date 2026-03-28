from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import time
import logging

from app.core.config import settings
from app.api.router import api_router
from app.db.mongodb import db_manager, get_db
from app.core.middleware import StandardResponseMiddleware, BackpressureMiddleware
from app.core.lifecycle import BackgroundGuardian
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
        description="TAC-PMC-CRM Supreme Hardened Backend"
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

    # ERROR HANDLING: Domain → HTTP
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": exc.message,
                "entity_id": exc.entity_id or "none",
                "error_type": exc.__class__.__name__
            }
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
            "timestamp": time.time()
        }

    return app

# The Authoritative Entry Point
app = create_app()
