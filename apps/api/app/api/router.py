from fastapi import APIRouter
from app.api.v1 import (
    auth_routes, user_routes, project_routes, client_routes, 
    payment_routes, site_routes, notification_routes, 
    work_order_routes, vendor_routes, settings_routes, 
    ai_summary_routes, reporting_routes, scheduler_routes, 
    cash_routes, audit_routes, dashboard_routes
)
# Fixed CR-02: Path updated to match new DDD structure
try:
    from app.modules.scheduler.api.routes import scheduler_router as enterprise_scheduler_router, portfolio_router
    HAS_V2 = True
except ImportError:
    HAS_V2 = False

# Central API Router (Point 21)
api_router = APIRouter()

# Registry: Version 1
v1_router = APIRouter()
v1_router.include_router(auth_routes.router, tags=["Authentication"])
v1_router.include_router(user_routes.router, tags=["Users"])
v1_router.include_router(project_routes.router, tags=["Projects"])
v1_router.include_router(client_routes.router, tags=["Clients"])
v1_router.include_router(payment_routes.router, tags=["Payments"])
v1_router.include_router(site_routes.router, tags=["Site Operations"])
v1_router.include_router(notification_routes.router, tags=["Notifications"])
v1_router.include_router(work_order_routes.router, tags=["Work Orders"])
v1_router.include_router(vendor_routes.router, tags=["Vendors"])
v1_router.include_router(settings_routes.router, tags=["Settings"])
v1_router.include_router(ai_summary_routes.router, tags=["AI Intelligence"])
v1_router.include_router(reporting_routes.router, tags=["Reporting"])
v1_router.include_router(scheduler_routes.router, tags=["PPM Scheduler"])
v1_router.include_router(cash_routes.router, tags=["Cash Flows"])
v1_router.include_router(audit_routes.router, tags=["Audit Logs"])
v1_router.include_router(dashboard_routes.router, tags=["Dashboard"])

# Mount Version 1
api_router.include_router(v1_router, prefix="/v1")

# Registry: Version 2 (Enterprise)
if HAS_V2:
    v2_router = APIRouter()
    v2_router.include_router(enterprise_scheduler_router, tags=["Enterprise Scheduler"])
    v2_router.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio management"])
    api_router.include_router(v2_router, prefix="/v2")
