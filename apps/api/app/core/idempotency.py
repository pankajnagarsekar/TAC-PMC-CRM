import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

async def check_idempotency(db, session, operation_key: str) -> bool:
    if not operation_key: return False
    existing = await db.operation_logs.find_one({"operation_key": operation_key}, session=session)
    if existing:
        logger.warning(f"Duplicate operation: {operation_key}")
        return True
    return False

async def record_operation(db, session, operation_key: str, entity_type: str, response_payload: dict = None) -> None:
    if not operation_key: return
    await db.operation_logs.insert_one({
        "operation_key": operation_key,
        "entity_type": entity_type,
        "response_payload": response_payload,
        "created_at": datetime.now(timezone.utc)
    }, session=session)
