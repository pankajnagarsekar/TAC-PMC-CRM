from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.project_service import ProjectService
from app.services.client_service import ClientService
from app.services.financial_service import FinancialService
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService
from app.services.site_service import SiteService
from app.services.work_order_service import WorkOrderService
from app.services.vendor_service import VendorService
from app.services.settings_service import SettingsService
from app.services.ai_summary_service import AISummaryService
from app.services.reporting_service import ReportingService
from app.services.scheduler_service import SchedulerService
from app.services.cash_service import CashService
from app.services.master_data_service import MasterDataService
from app.services.snapshot_service import SnapshotService
from app.services.dashboard_service import DashboardService
from app.core.dependencies import PermissionChecker

async def get_audit_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> AuditService:
    return AuditService(db)

async def get_permission_checker(db: AsyncIOMotorDatabase = Depends(get_db)) -> PermissionChecker:
    return PermissionChecker(db)

async def get_auth_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> AuthService:
    return AuthService(db)

async def get_snapshot_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> SnapshotService:
    return SnapshotService(db)

async def get_financial_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> FinancialService:
    return FinancialService(db)

async def get_user_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
    permission_checker: PermissionChecker = Depends(get_permission_checker)
) -> UserService:
    return UserService(db, audit_service, permission_checker)

async def get_project_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
    financial_service: FinancialService = Depends(get_financial_service)
) -> ProjectService:
    return ProjectService(db, audit_service, permission_checker, financial_service)

async def get_client_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service)
) -> ClientService:
    return ClientService(db, audit_service)

async def get_payment_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
    financial_service: FinancialService = Depends(get_financial_service),
    permission_checker: PermissionChecker = Depends(get_permission_checker)
) -> PaymentService:
    return PaymentService(db, audit_service, financial_service, permission_checker)

async def get_notification_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> NotificationService:
    return NotificationService(db)

async def get_site_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
    permission_checker: PermissionChecker = Depends(get_permission_checker),
    snapshot_service: SnapshotService = Depends(get_snapshot_service)
) -> SiteService:
    return SiteService(db, audit_service, permission_checker, snapshot_service)

async def get_work_order_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
    financial_service: FinancialService = Depends(get_financial_service),
    permission_checker: PermissionChecker = Depends(get_permission_checker)
) -> WorkOrderService:
    return WorkOrderService(db, audit_service, financial_service, permission_checker)

async def get_vendor_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
    permission_checker: PermissionChecker = Depends(get_permission_checker)
) -> VendorService:
    return VendorService(db, audit_service, permission_checker)

async def get_settings_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    permission_checker: PermissionChecker = Depends(get_permission_checker)
) -> SettingsService:
    return SettingsService(db, permission_checker)

async def get_ai_summary_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    permission_checker: PermissionChecker = Depends(get_permission_checker)
) -> AISummaryService:
    return AISummaryService(db, permission_checker)

async def get_reporting_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    permission_checker: PermissionChecker = Depends(get_permission_checker)
) -> ReportingService:
    return ReportingService(db, permission_checker)

async def get_scheduler_service(db: AsyncIOMotorDatabase = Depends(get_db)):
    from app.core.dependencies import PermissionChecker
    return SchedulerService(db, PermissionChecker(db))

async def get_cash_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service)
):
    from app.core.dependencies import PermissionChecker
    return CashService(db, PermissionChecker(db), audit_service)

async def get_dashboard_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> DashboardService:
    return DashboardService(db)

async def get_master_data_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> MasterDataService:
    return MasterDataService(db)
