from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_db
from app.services.audit_service import AuditService
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
from app.core.dependencies import PermissionChecker

async def get_audit_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> AuditService:
    return AuditService(db)

async def get_permission_checker() -> PermissionChecker:
    return PermissionChecker()

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
    audit_service: AuditService = Depends(get_audit_service)
) -> PaymentService:
    return PaymentService(db, audit_service)

async def get_notification_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> NotificationService:
    return NotificationService(db)

async def get_site_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service)
) -> SiteService:
    return SiteService(db, audit_service)

async def get_work_order_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
    financial_service: FinancialService = Depends(get_financial_service)
) -> WorkOrderService:
    return WorkOrderService(db, audit_service, financial_service)

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
