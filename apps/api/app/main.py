from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import os

from app.core.config import settings
from app.api.v1.user_routes import router as user_router
from app.api.v1.project_routes import router as project_router
from app.api.v1.client_routes import router as client_router
from app.api.v1.payment_routes import router as payment_router
from app.api.v1.site_routes import router as site_router
from app.api.v1.notification_routes import router as notification_router
from app.api.v1.work_order_routes import router as work_order_router
from app.api.v1.vendor_routes import router as vendor_router
from app.api.v1.settings_routes import router as settings_router
from app.api.v1.ai_summary_routes import router as ai_summary_router
from app.api.v1.reporting_routes import router as reporting_router
from app.api.v1.scheduler_routes import router as scheduler_router
from app.api.v1.cash_routes import router as cash_router
from app.api.v1.audit_routes import router as audit_router
from app.api.v1.auth_routes import router as auth_router
from execution.scheduler.api.routes import scheduler_router as enterprise_scheduler_router, portfolio_router
from app.db.mongodb import db_manager

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="2.0.0",
        description="Restructured TAC-PMC-CRM Backend"
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # Tighten in production via settings
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    v1_routers = [
        user_router, project_router, client_router, payment_router,
        site_router, notification_router, work_order_router, vendor_router,
        settings_router, ai_summary_router, reporting_router, scheduler_router,
        cash_router, audit_router, auth_router
    ]
    
    for router in v1_routers:
        app.include_router(router, prefix="/api/v1")
        app.include_router(router, prefix="/api")
    
    # Enterprise Scheduler V2
    app.include_router(enterprise_scheduler_router, prefix="/api/v2")
    app.include_router(portfolio_router, prefix="/api/v2/portfolio")

    @app.on_event("startup")
    async def startup_db_client():
        db_manager.connect(settings.MONGO_URL, settings.DB_NAME)

    @app.on_event("shutdown")
    async def shutdown_db_client():
        db_manager.disconnect()

    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": "2.0.0-restructured"}

    return app

app = create_app()
