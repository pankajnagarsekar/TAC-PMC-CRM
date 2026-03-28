import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Dict, Any
from app.core.time import now
from app.modules.financial.domain.financial_engine import FinancialEngine

logger = logging.getLogger(__name__)

class IdempotencyGuard:
    """
    Sovereign Guard against double-spend and duplicate operations (Point 81, 102).
    Uses Fingerprinting (Point 81) to identify logical duplicates beyond request nonces.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_or_set(self, key: str, context: Dict[str, Any], session=None) -> Optional[Dict[str, Any]]:
        """
        Check if operation has already occurred.
        If yes, return existing response.
        If no, return None (calling code proceeds).
        """
        if not key: return None

        # Logic-level fingerprint (Point 81)
        # Prevents same payment data from being sent with different req_ids
        fingerprint = FinancialEngine.generate_fingerprint(context)
        
        # Primary search by fingerprint (Safety First)
        existing = await self.db.idempotency_store.find_one({
            "$or": [
                {"operation_key": key},
                {"fingerprint": fingerprint}
            ]
        }, session=session)

        if existing:
            logger.warning(f"IDEMPOTENCY_HIT: {key} / FP: {fingerprint}")
            return existing.get("response")
            
        return None

    async def finalize(self, key: str, context: Dict[str, Any], response: Dict[str, Any], session=None):
        """Seal the operation record."""
        if not key: return
        
        fingerprint = FinancialEngine.generate_fingerprint(context)
        await self.db.idempotency_store.insert_one({
            "operation_key": key,
            "fingerprint": fingerprint,
            "response": response,
            "created_at": now()
        }, session=session)
