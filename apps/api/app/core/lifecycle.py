import asyncio
import logging
import time

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.consistency import ConsistencyGuardian
from app.core.concurrency import ConcurrencyManager

logger = logging.getLogger(__name__)


class BackgroundGuardian:
    """
    Sovereign Maintenance Controller (Point 103, 118, 122).
    Executes periodic reconciliation and cleanup to ensure long-term survivability.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.guardian = ConsistencyGuardian(db)
        self.active = False
        self._task = None
        self._concurrency_manager = None  # Lazy loading (BUG-31)

    async def start(self):
        """Boot maintenance loops."""
        self.active = True
        if self._concurrency_manager is None:
            self._concurrency_manager = ConcurrencyManager()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("BACKGROUND_GUARDIAN: Maintenance loops initiated.")

    async def stop(self):
        """Graceful shutdown (Point 118)."""
        self.active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BACKGROUND_GUARDIAN: Maintenance loops halted.")

    async def _run_loop(self):
        while self.active:
            try:
                # 1. Purge request nonces > 24h (Point 102)
                yesterday = time.time() - (24 * 3600)
                res = await self.db.request_nonces.delete_many(
                    {"used_at": {"$lt": yesterday}}
                )
                if res.deleted_count > 0:
                    logger.info(f"GUARDIAN: Purged {res.deleted_count} expired nonces.")

                # 2. Detect Zombie Records (Point 103)
                # Fixed CR-17: AlertService is triggered internally by find_zombies()
                zombies = await self.guardian.find_zombies()
                if zombies and len(zombies) > 0:
                    logger.warning(
                        f"INTEGRITY_ALERT: Detected {len(zombies)} zombie records. Alerts have been raised."
                    )

                # 3. Scheduled Reconciliation (Point 61)
                # This could be expensive, so we run it incrementally or per project
                # For now, just a heart-beat check

                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"GUARDIAN_LOOP_FAULT: {e}")
                await asyncio.sleep(60)  # Back off on error

    @staticmethod
    async def mongodb_health_check(db):
        """Authoritative DB Health Probe (Point 6, BUG-06)."""
        try:
            await db.command("ping")
            return True
        except Exception as e:
            logger.error(f"HEALTH_CHECK_FAILURE: MongoDB unreachable: {e}")
            return False


def register_exception_handlers(app):
    """
    Centralized Fault Normalization (Point 10, BUG-10).
    Ensures all unhandled exceptions return structured JSON.
    """
    from fastapi import Request, status
    from fastapi.responses import JSONResponse
    from app.modules.shared.domain.exceptions import DomainError

    @app.exception_handler(DomainError)
    async def domain_fault_handler(request: Request, exc: DomainError):
        from app.modules.shared.domain.exceptions import ValidationError, NotFoundError
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(exc, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, ValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": "DOMAIN_FAULT",
                    "message": str(exc),
                    "type": exc.__class__.__name__
                }
            }
        )

    @app.exception_handler(Exception)
    async def system_fault_handler(request: Request, exc: Exception):
        logger.error(f"SYSTEM_FATAL: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SYSTEM_FAULT",
                    "message": "A critical system error occurred.",
                    "type": "InternalError"
                }
            }
        )
