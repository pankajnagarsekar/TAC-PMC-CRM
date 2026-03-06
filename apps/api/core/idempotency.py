"""
Idempotency utilities for financial operations.
Prevents duplicate transaction execution via operation_logs collection.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def check_idempotency(db, session, operation_key: str) -> dict:
    """
    Check if an operation has already been executed.
    Returns the record if it is a DUPLICATE (already exists), else None.
    """
    if not operation_key:
        return None

    existing = await db.operation_logs.find_one(
        {"operation_key": operation_key},
        session=session
    )

    if existing:
        logger.warning(f"Duplicate operation detected: {operation_key}")
        return existing

    return None


async def record_operation(db, session, operation_key: str, entity_type: str, response_payload: dict = None) -> None:
    """
    Record a completed operation for idempotency tracking.
    Should be called within the same transaction as the main operation.
    """
    if not operation_key:
        return

    await db.operation_logs.insert_one(
        {
            "operation_key": operation_key,
            "entity_type": entity_type,
            "response_payload": response_payload,
            "created_at": datetime.utcnow(),
        },
        session=session
    )
    logger.info(f"Recorded operation: {operation_key} ({entity_type})")
