"""
Idempotency utilities for financial operations.
Prevents duplicate transaction execution via operation_logs collection.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


async def check_idempotency(db, session, operation_key: str) -> bool:
    """
    Check if an operation has already been executed.
    Returns True if the operation is a DUPLICATE (already exists), else False.
    """
    if not operation_key:
        return False

    existing = await db.operation_logs.find_one(
        {"operation_key": operation_key},
        session=session
    )

    if existing:
        logger.warning(f"Duplicate operation detected: {operation_key}")
        return True

    return False


async def get_recorded_operation(db, session, operation_key: str) -> Optional[dict]:
    """
    Retrieve a recorded operation's full response payload.
    Returns the response_payload dict if found, else None.
    Use this for deterministic replay of prior successful responses.
    """
    if not operation_key:
        return None

    existing = await db.operation_logs.find_one(
        {"operation_key": operation_key},
        session=session
    )

    if existing and existing.get("response_payload"):
        logger.info(f"Found recorded operation: {operation_key}")
        return existing["response_payload"]

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
            "created_at": datetime.now(timezone.utc),
        },
        session=session
    )
    logger.info(f"Recorded operation: {operation_key} ({entity_type})")
