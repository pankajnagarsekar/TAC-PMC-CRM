import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClientSession, AsyncIOMotorDatabase

from app.modules.contracting.infrastructure.repository import (
    LedgerRepository,
    RetentionReleaseRepository,
    VendorRepository,
    WorkOrderRepository,

)
from app.modules.financial.infrastructure.repository import (
    CashTransactionRepository,
    CodeMasterRepository,
    FundAllocationRepository,
    PCRepository,
)
from app.modules.project.infrastructure.repository import (
    BudgetRepository,
    ProjectRepository,
)
from app.modules.shared.infrastructure.sequence_repo import SequenceRepository
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
        self.vendors = VendorRepository(db)
        self.ledger = LedgerRepository(db)
        self.sequences = SequenceRepository(db)
        self.code_master = CodeMasterRepository(db)
        self.retention_releases = RetentionReleaseRepository(db)

    async def __aenter__(self):
        """Start transaction session."""
        try:
            self.session = await self.client.start_session()
            self.session.start_transaction()
            # Force validation with a supported command (Point 75: Hardened Probe)
            # find_one is supported in transactions, ping is NOT.
            await self.db.idempotency_store.find_one({"_id": "probe"}, session=self.session)
        except Exception as e:
            # Fallback for standalone MongoDB (Testing context - Point 75)
            # Transaction numbers are only allowed on replica sets
            print(f"UOW DEBUG: start_transaction failed: {e}")
            if "Transaction numbers" in str(e) or "IllegalOperation" in str(type(e).__name__):
                logger.warning(
                    "UOW: MongoDB Transactions NOT SUPPORTED (Standalone mode). "
                    "Proceeding without session/transaction."
                )
                # If transactions fail, we probably can't use sessions reliably for atomicity here
                # Nullify session so repositories don't use it
                self.session = None
            else:
                raise e

        # Inject session into all managed repos (Stateful UOW - BUG-04)
        repo_names = [
            'projects', 'work_orders', 'payments', 'budgets',
            'cash_transactions', 'fund_allocations', 'dprs',
            'vendors', 'ledger', 'sequences', 'code_master',
            'retention_releases'
        ]
        for name in repo_names:
            repo = getattr(self, name)
            if repo:
                repo.session = self.session

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Finalize transaction."""
        if self.session and self.session.in_transaction:
            if exc_type:
                logger.warning(f"UOW_ROLLBACK: Atomicity failure detected: {exc_val}")
                await self.session.abort_transaction()
            else:
                await self.session.commit_transaction()

        if self.session:
            await self.session.end_session()

    async def commit(self):
        """Manually commit."""
        if self.session and self.session.in_transaction:
            await self.session.commit_transaction()

    async def rollback(self):
        """Manually rollback."""
        if self.session and self.session.in_transaction:
            await self.session.abort_transaction()
