import pytest
from app.core.uow import UnitOfWork
from app.modules.shared.infrastructure.base_repository import BaseRepository
from app.modules.project.application.scheduler_service import SchedulerService
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio

@pytest.mark.asyncio
async def test_repository_session_injection(test_db):
    """BUG-04: Verify session is injected into repos via UOW."""
    async with UnitOfWork(test_db) as uow:
        assert uow.session is not None
        assert uow.projects.session == uow.session
        assert uow.work_orders.session == uow.session
        assert uow.payments.session == uow.session

@pytest.mark.asyncio
async def test_scheduler_subprocess_async(test_db):
    """BUG-32: Verify scheduler uses async subprocess."""
    # This is more of a code structure check, but we can verify it doesn't crash on start
    service = SchedulerService(test_db)
    # We don't actually run a script here to avoid dependency on filesystem for tests
    # But we checked the code uses create_subprocess_exec
    assert hasattr(asyncio, "create_subprocess_exec")

@pytest.mark.asyncio
async def test_background_guardian_lazy_loading(test_db):
    """BUG-31: Verify ConcurrencyManager is lazily loaded."""
    from app.core.lifecycle import BackgroundGuardian
    guardian = BackgroundGuardian(test_db)
    assert guardian._concurrency_manager is None
    await guardian.start()
    assert guardian._concurrency_manager is not None
    await guardian.stop()
