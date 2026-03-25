"""
Transaction middleware for the PPM Scheduler.
Enforces atomicity for schedule recalculations.

Constitution §4 Step 7 / Tech Arch §3.2:
    The engine returns results for N tasks.
    The API must persist all N tasks using a single MongoDB bulkWrite transaction.
    If the transaction fails, the entire schedule state rolls back.
"""
import logging
from typing import AsyncGenerator
from fastapi import Depends
from core.database import db_manager

logger = logging.getLogger(__name__)

async def get_transaction_session() -> AsyncGenerator:
    """
    FastAPI dependency that provides a MongoDB session with an active transaction.
    """
    async with db_manager.transaction_session() as session:
        yield session
