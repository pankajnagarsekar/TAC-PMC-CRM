from fastapi import HTTPException, status, Depends, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional, List
import logging

from app.db.mongodb import get_db
from app.modules.shared.application.audit_service import AuditService
from app.modules.identity.application.auth_service import AuthService
from app.modules.identity.application.user_service import UserService
from app.modules.project.application.project_service import ProjectService
from app.modules.project.application.client_service import ClientService
from app.modules.project.application.timeline_service import TimelineService
from app.modules.financial.application.financial_service import FinancialService
from app.modules.financial.application.payment_service import PaymentService
from app.modules.financial.application.cash_service import CashService
from app.modules.site_operations.application.site_service import SiteService
from app.modules.shared.application.notification_service import NotificationService
from app.modules.contracting.application.work_order_service import WorkOrderService
from app.modules.contracting.application.vendor_service import VendorService
from app.modules.identity.application.settings_service import SettingsService
from app.modules.reporting.application.reporting_service import ReportingService
from app.modules.reporting.application.dashboard_service import DashboardService
from app.modules.reporting.application.ai_summary_service import AISummaryService
from app.modules.reporting.application.ai_service import AIService
from app.modules.project.application.scheduler_service import SchedulerService
from app.modules.financial.application.master_data_service import MasterDataService
from app.modules.shared.application.alert_service import AlertService
from app.modules.shared.application.snapshot_service import SnapshotService

from app.core.permissions import PermissionChecker
from app.core.resilience import NonceGuard
from app.modules.identity.infrastructure.repository import UserRepository

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# --- AUTHENTICATION DEPENDENCIES ---

async def get_auth_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> AuthService:
    """Inject instance-based AuthService (Point 3, 22)"""
    return AuthService(db)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """Retrieve user from token with revocation and skew checks (Point 101, 102)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = credentials.credentials
    try:
        payload = await auth_service.decode_token(token, "access")
        user_id: str = payload.get("user_id")
        if not user_id:
             raise HTTPException(status_code=401, detail="Invalid token payload")
        return payload
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"AUTH_FAILURE: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")

async def get_authenticated_user(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """Validate user exists in DB and is active (Point 3, 63, Fixed CR-23)"""
    user_id = current_user.get("user_id")
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    
    # Authoritative active check via checker
    await PermissionChecker.validate_active_user(user)
    return user

# --- RESILIENCE DEPENDENCIES (Point 102) ---

async def verify_nonce(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
    user: dict = Depends(get_authenticated_user)
):
    """Authoritative Nonce Verification for Write Operations."""
    nonce = request.headers.get("X-Request-Nonce")
    guard = NonceGuard(db)
    await guard.verify(nonce, user["user_id"])
    return nonce

# --- PERMISSION DEPENDENCIES ---

async def get_permission_checker(db: AsyncIOMotorDatabase = Depends(get_db)) -> PermissionChecker:
    return PermissionChecker(db)

# --- SERVICE PROVIDERS (Point 2) ---

async def get_audit_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> AuditService:
    return AuditService(db)

async def get_snapshot_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> SnapshotService:
    return SnapshotService(db)

async def get_financial_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> FinancialService:
    return FinancialService(db)

async def get_user_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    perm: PermissionChecker = Depends(get_permission_checker)
) -> UserService:
    return UserService(db, audit, perm)

async def get_project_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    perm: PermissionChecker = Depends(get_permission_checker),
    fin: FinancialService = Depends(get_financial_service)
) -> ProjectService:
    return ProjectService(db, audit, perm, fin)

async def get_client_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service)
) -> ClientService:
    return ClientService(db, audit)

async def get_payment_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    fin: FinancialService = Depends(get_financial_service),
    perm: PermissionChecker = Depends(get_permission_checker)
) -> PaymentService:
    return PaymentService(db, audit, fin, perm)

async def get_site_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    perm: PermissionChecker = Depends(get_permission_checker),
    snap: SnapshotService = Depends(get_snapshot_service)
) -> SiteService:
    return SiteService(db, audit, perm, snap)

async def get_work_order_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    fin: FinancialService = Depends(get_financial_service),
    perm: PermissionChecker = Depends(get_permission_checker)
) -> WorkOrderService:
    return WorkOrderService(db, audit, fin, perm)

async def get_vendor_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    perm: PermissionChecker = Depends(get_permission_checker)
) -> VendorService:
    return VendorService(db, audit, perm)

async def get_settings_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    perm: PermissionChecker = Depends(get_permission_checker),
    audit: AuditService = Depends(get_audit_service)
) -> SettingsService:
    return SettingsService(db, perm, audit)

async def get_reporting_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    perm: PermissionChecker = Depends(get_permission_checker)
) -> ReportingService:
    return ReportingService(db, perm)

async def get_cash_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    perm: PermissionChecker = Depends(get_permission_checker),
    audit: AuditService = Depends(get_audit_service)
) -> CashService:
    return CashService(db, perm, audit)

async def get_dashboard_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> DashboardService:
    return DashboardService(db)

async def get_master_data_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service)
) -> MasterDataService:
    return MasterDataService(db, audit)

async def get_notification_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit: AuditService = Depends(get_audit_service)
) -> NotificationService:
    return NotificationService(db, audit)

async def get_ai_summary_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    perm: PermissionChecker = Depends(get_permission_checker)
) -> AISummaryService:
    return AISummaryService(db, perm)

async def get_ai_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> AIService:
    return AIService(db)

async def get_scheduler_service(
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> SchedulerService:
    return SchedulerService(db)

async def get_alert_service(
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> AlertService:
    return AlertService(db)
