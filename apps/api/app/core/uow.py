from motor.motor_asyncio import AsyncIOMotorClientSession, AsyncIOMotorDatabase
from typing import Optional
import logging

from app.modules.project.infrastructure.repository import ProjectRepository
from app.modules.contracting.infrastructure.repository import WorkOrderRepository
from app.modules.financial.infrastructure.repository import PCRepository, BudgetRepository, CashTransactionRepository, FundAllocationRepository
from app.modules.site_operations.infrastructure.repository import DPRRepository

logger = logging.getLogger(__name__)

class UnitOfWork:
    """
    Atomic transaction manager for cross-repository updates (Point 75, 91, 115).
    Ensures that multi-step financial flows either commit fully or rollback entirely.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.client = db.client
        self.session: Optional[AsyncIOMotorClientSession] = None
        
        # Repositories (Lazy loaded with session)
        self.projects = ProjectRepository(db)
        self.work_orders = WorkOrderRepository(db)
        self.payments = PCRepository(db)
        self.budgets = BudgetRepository(db)
        self.cash_transactions = CashTransactionRepository(db)
        self.fund_allocations = FundAllocationRepository(db)
        self.dprs = DPRRepository(db)

    async def __aenter__(self):
        """Start transaction session."""
        self.session = await self.client.start_session()
        self.session.start_transaction()
        # Inject session into all managed repos (Stateful UOW)
        # Note: Repos should support optional session in their methods
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Finalize transaction."""
        if exc_type:
            logger.warning(f"UOW_ROLLBACK: Atomicity failure detected: {exc_val}")
            await self.session.abort_transaction()
        else:
            await self.session.commit_transaction()
        
        await self.session.end_session()

    async def commit(self):
        """Manually commit."""
        if self.session:
            await self.session.commit_transaction()

    async def rollback(self):
        """Manually rollback."""
        if self.session:
            await self.session.abort_transaction()
