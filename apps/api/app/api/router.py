from fastapi import APIRouter

from app.modules.contracting.api.routes import router as contracting_router
from app.modules.financial.api.routes import router as financial_router
from app.modules.identity.api.routes import router as identity_router
from app.modules.project.api.routes import router as project_router
from app.modules.reporting.api.routes import router as reporting_router
from app.modules.shared.api.routes import router as shared_router
from app.modules.site_operations.api.routes import router as site_operations_router
from app.api.v1.jobs import router as jobs_router

# ... (HAS_V2 logic)
v1_router.include_router(jobs_router)
v1_router.include_router(identity_router)  # Handles /auth, /users, /settings
v1_router.include_router(contracting_router)  # Handles /vendors, /work-orders
v1_router.include_router(project_router)  # Handles /projects, /clients, /scheduler
v1_router.include_router(site_operations_router)  # Handles /site logic
v1_router.include_router(financial_router)  # Handles /payments, /cash, /settings/codes
v1_router.include_router(reporting_router)  # Handles /reports, project dashboard
v1_router.include_router(shared_router)  # Handles /notifications, /audit

# Mount Version 1
api_router.include_router(v1_router, prefix="/v1")

# Registry: Version 2 (Enterprise)
# if HAS_V2:
#     v2_router = APIRouter()
#     v2_router.include_router(enterprise_scheduler_router, tags=["Enterprise Scheduler"])
#     v2_router.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio management"])
#     api_router.include_router(v2_router, prefix="/v2")
