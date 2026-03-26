import time
import logging
from typing import Dict, Optional, Callable, Any
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Sovereign Circuit Breaker for External Dependencies (Point 125).
    Safeguards the system from Cascading Failures when AI/OCR APIs hang.
    """
    def __init__(self, name: str, threshold: int = 5, recovery_timeout: int = 60):
        self.name = name
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(f"CIRCUIT_BREAKER [{self.name}]: Transitioning to HALF_OPEN")
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"EXTERNAL_SERVICE_UNAVAILABLE: Circuit breaker '{self.name}' is OPEN."
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def _on_failure(self, error):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.threshold:
            self.state = "OPEN"
            logger.critical(f"CIRCUIT_BREAKER [{self.name}]: OPENED due to: {error}")

class NonceGuard:
    """
    Global Replay Protection System (Point 102).
    Prevents same request from being processed multiple times.
    """
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def verify(self, nonce: str, user_id: str):
        """Block if nonce has been used in the last 24 hours."""
        if not nonce:
            raise HTTPException(status_code=400, detail="NONCE_REQUIRED: X-Request-Nonce header is missing.")
            
        existing = await self.db.request_nonces.find_one({"nonce": nonce, "user_id": user_id})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="REPLAY_ATTACK_DETECTED: This request has already been processed."
            )
        
        await self.db.request_nonces.insert_one({
            "nonce": nonce,
            "user_id": user_id,
            "used_at": time.time()
        })

# GLOBAL BREAKER REGISTRY
ai_breaker = CircuitBreaker("GEMINI_AI")
ocr_breaker = CircuitBreaker("OCR_ENGINE")
pdf_breaker = CircuitBreaker("PDF_SERVICE")
