import logging
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.time import now
from app.modules.shared.domain.financial_engine import FinancialEngine

logger = logging.getLogger(__name__)


class IdempotencyGuard:
    """
    Sovereign Guard against double-spend and duplicate operations (Point 81, 102).
    Uses Fingerprinting (Point 81) to identify logical duplicates beyond request nonces.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_or_set(
        self, key: str, context: Dict[str, Any], session=None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if operation has already occurred.
        If yes, return existing response.
        If no, return None (calling code proceeds).
        """
        if not key:
            return None

        # Logic-level fingerprint (Point 81)
        # Prevents same payment data from being sent with different req_ids
        fingerprint = FinancialEngine.generate_fingerprint(context)

        # Primary search by fingerprint (Safety First)
        existing = await self.db.idempotency_store.find_one(
            {"$or": [{"operation_key": key}, {"fingerprint": fingerprint}]},
            session=session,
        )

        if existing:
            logger.warning(f"IDEMPOTENCY_HIT: {key} / FP: {fingerprint}")
            return existing.get("response")

        return None

    async def finalize(
        self, key: str, context: Dict[str, Any], response: Dict[str, Any], session=None
    ):
        """Seal the operation record."""
        if not key:
            return

        fingerprint = FinancialEngine.generate_fingerprint(context)
        await self.db.idempotency_store.insert_one(
            {
                "operation_key": key,
                "fingerprint": fingerprint,
                "response": response,
                "created_at": now(),
            },
            session=session,
        )


async def get_recorded_operation(
    db: AsyncIOMotorDatabase, session, key: str, context: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Standalone wrapper for IdempotencyGuard.get_or_set (Point 81)."""
    guard = IdempotencyGuard(db)
    # If context is not provided, we only search by key (Legacy compatibility)
    if not context:
        existing = await db.idempotency_store.find_one(
            {"operation_key": key}, session=session
        )
        return existing.get("response") if existing else None

    return await guard.get_or_set(key, context, session=session)


async def record_operation(
    db: AsyncIOMotorDatabase,
    session,
    key: str,
    operation_type: str,
    response_payload: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
):
    """Standalone wrapper for IdempotencyGuard.finalize (Point 81)."""
    guard = IdempotencyGuard(db)
    # If context is not provided, use a dummy one to avoid hash failure
    # and maintain key-based lookup
    if not context:
        context = {"key": key, "type": operation_type}

    await guard.finalize(key, context, response_payload, session=session)
