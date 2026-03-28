from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """System Constitution: Database Sovereignty (Point 7)."""
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self, mongo_url: str, db_name: str):
        """Establish authoritative connection with hard ping."""
        try:
            self.client = AsyncIOMotorClient(mongo_url)
            self.db = self.client[db_name]
            # Hard Ping (Point 7)
            await self.client.admin.command('ping')
            logger.info(f"LIFECYCLE: Connected to MongoDB ({db_name})")
            
            # Fixed CR-21: Trigger index creation on startup
            await self.initialize_indexes()
            
        except Exception as e:
            logger.error(f"LIFECYCLE_FATAL: MongoDB connection failed: {e}")
            raise

    async def initialize_indexes(self):
        """Fixed CR-21: Authoritative index enforcement for all repositories."""
        if self.db is None: return
        
        logger.info("LIFECYCLE: Enforcing database indexes...")
        # Import inside to avoid circular deps
        from app.modules.identity.infrastructure.repository import UserRepository, UserProjectMapRepository
        from app.modules.project.infrastructure.repository import ProjectRepository, ClientRepository
        from app.modules.contracting.infrastructure.repository import WorkOrderRepository, VendorRepository
        from app.modules.financial.infrastructure.repository import PCRepository, BudgetRepository, CodeMasterRepository, FinancialStateRepository
        from app.modules.site_operations.infrastructure.repository import DPRRepository, WorkerLogRepository, AttendanceRepository
        from app.modules.shared.infrastructure.repository import NotificationRepository, AuditRepository, AlertRepository
        
        repos = [
            UserRepository(self.db), UserProjectMapRepository(self.db),
            ProjectRepository(self.db), WorkOrderRepository(self.db),
            PCRepository(self.db), BudgetRepository(self.db),
            CodeMasterRepository(self.db), FinancialStateRepository(self.db),
            VendorRepository(self.db), ClientRepository(self.db),
            DPRRepository(self.db), WorkerLogRepository(self.db),
            AttendanceRepository(self.db), NotificationRepository(self.db),
            AuditRepository(self.db), AlertRepository(self.db)
        ]
        
        for repo in repos:
            try:
                await repo.ensure_indexes()
            except Exception as e:
                logger.error(f"INDEX_OVERSIGHT: Failed for {repo.__class__.__name__}: {e}")

    def close(self):
        """Graceful termination (Point 118)."""
        if self.client:
            self.client.close()
            logger.info("LIFECYCLE: MongoDB connection closed gracefully")

    def get_db(self) -> AsyncIOMotorDatabase:
        """Access the database instance (Point 7)."""
        if self.db is None:
            raise RuntimeError("DATABASE_DOMAIN_ERROR: Engine not initialized. Access blocked.")
        return self.db

# Global singleton for app lifecycle management (Point 7)
db_manager = DatabaseManager()

async def get_db() -> AsyncIOMotorDatabase:
    """Dependency injection provider for database."""
    return db_manager.get_db()
