from fastapi import APIRouter
from app.api.v1 import (
    auth_routes, user_routes, project_routes, client_routes, 
    payment_routes, site_routes, notification_routes, 
    work_order_routes, vendor_routes, settings_routes, 
    ai_summary_routes, reporting_routes, scheduler_routes, 
    cash_routes, audit_routes, dashboard_routes
)
from execution.scheduler.api.routes import scheduler_router as enterprise_scheduler_router, portfolio_router

# Central API Router (Point 21)
api_router = APIRouter()

# Registry: Version 1
v1_router = APIRouter()
v1_router.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(user_routes.router, prefix="/users", tags=["Users"])
v1_router.include_router(project_routes.router, prefix="/projects", tags=["Projects"])
v1_router.include_router(client_routes.router, prefix="/clients", tags=["Clients"])
v1_router.include_router(payment_routes.router, prefix="/payments", tags=["Payments"])
v1_router.include_router(site_routes.router, prefix="/site", tags=["Site Operations"])
v1_router.include_router(notification_routes.router, prefix="/notifications", tags=["Notifications"])
v1_router.include_router(work_order_routes.router, prefix="/work-orders", tags=["Work Orders"])
v1_router.include_router(vendor_routes.router, prefix="/vendors", tags=["Vendors"])
v1_router.include_router(settings_routes.router, prefix="/settings", tags=["Settings"])
v1_router.include_router(ai_summary_routes.router, prefix="/ai", tags=["AI Intelligence"])
v1_router.include_router(reporting_routes.router, prefix="/reports", tags=["Reporting"])
v1_router.include_router(scheduler_routes.router, prefix="/scheduler", tags=["PPM Scheduler"])
v1_router.include_router(cash_routes.router, prefix="/cash", tags=["Cash Flows"])
v1_router.include_router(audit_routes.router, prefix="/audit", tags=["Audit Logs"])
v1_router.include_router(dashboard_routes.router, prefix="/dashboard", tags=["Dashboard"])

# Registry: Version 2 (Enterprise)
v2_router = APIRouter()
v2_router.include_router(enterprise_scheduler_router, tags=["Enterprise Scheduler"])
v2_router.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio management"])

# Mount Versions
api_router.include_router(v1_router, prefix="/v1")
api_router.include_router(v2_router, prefix="/v2")
