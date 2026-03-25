"""
Idempotency middleware/dependency for the PPM Scheduler.

Constitution §3.3 / Schema §3.3:
    Every write request includes an idempotency_key (UUID).
    API caches response for a given key for 5 minutes.
    Duplicate requests return cached response without re-executing.
"""
import logging
from typing import Optional, Dict, Any, Callable
from pydantic import BaseModel
from fastapi import Request, HTTPException, Depends
from core.idempotency import get_recorded_operation, record_operation
from core.database import get_db, db_manager

logger = logging.getLogger(__name__)

# TTL is enforced by a TTL index on operation_logs.created_at in MongoDB
# or handled via logic. The core record_operation uses current time.

async def handle_idempotency(
    request: Request,
    db = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to check for existing idempotency keys.
    Can be used in any mutating route that receives an idempotency_key in the body.
    """
    # Note: Because the idempotency_key is inside the Pydantic body models
    # like ScheduleChangeRequest, we can't easily extract it from the raw Request
    # without consuming the stream or duplicate effort.
    # Instead, each route will call get_recorded_operation manually 
    # using the key from the validated request body.
    pass

async def check_duplicate(db, idempotency_key: str) -> Optional[Dict[str, Any]]:
    """
    Returns the cached response payload if this key has already been processed.
    Returns None otherwise.
    """
    if not idempotency_key:
        return None
    
    # Check if we have a recorded operation for this key
    # We use None for session since read is fine without transaction here
    cached = await get_recorded_operation(db, None, idempotency_key)
    if cached:
        logger.info(f"Idempotency hit: {idempotency_key}")
        return cached
    
    return None

async def save_idempotent_response(
    db, 
    session, 
    idempotency_key: str, 
    entity_type: str, 
    response: Dict[str, Any]
) -> None:
    """
    Records the operation result for future deduplication.
    MUST be called within the same transaction that saved the data.
    """
    if not idempotency_key:
        return
        
    await record_operation(
        db=db,
        session=session,
        operation_key=idempotency_key,
        entity_type=entity_type,
        response_payload=response
    )
