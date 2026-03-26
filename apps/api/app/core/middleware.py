import time
import logging
import uuid
from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Any, Dict, Optional

from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

class StandardResponseMiddleware(BaseHTTPMiddleware):
    """
    Sovereign Response Wrapper (Point 4, 10).
    Injects tracing metadata, enforces rate limits, and normalizes system faults.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # 1. RATE LIMIT ENFORCEMENT (Point 5, 116)
        identity = request.headers.get("Authorization", request.client.host)
        if request.url.path not in ["/docs", "/redoc", "/openapi.json"]:
            try:
                # Custom tiering could be added based on route
                tier = "Heavy" if "export" in request.url.path or "report" in request.url.path else "Standard"
                await limiter.check(identity, tier=tier)
            except HTTPException as he:
                return self._standard_error(he.status_code, he.detail, request_id, start_time)

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
                return response

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            return response

        except HTTPException as he:
            return self._standard_error(he.status_code, he.detail, request_id, start_time)
            
        except Exception as exc:
            logger.error(f"SYSTEM_FAULT: {exc} | ID: {request_id}", exc_info=True)
            return self._standard_error(
                status.HTTP_500_INTERNAL_SERVER_ERROR, 
                "A critical system fault occurred.", 
                request_id, 
                start_time
            )

    def _standard_error(self, code: int, message: Any, request_id: str, start_time: float):
        process_time = time.time() - start_time
        return JSONResponse(
            status_code=code,
            content={
                "success": False,
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id
                },
                "meta": {
                    "process_time": process_time
                }
            }
        )

class BackpressureMiddleware(BaseHTTPMiddleware):
    """
    Saturation Guard (Point 105).
    Immediate rejection when system concurrency limit is reached.
    """
    active_requests = 0
    MAX_CONCURRENT = 100

    async def dispatch(self, request: Request, call_next):
        if BackpressureMiddleware.active_requests >= BackpressureMiddleware.MAX_CONCURRENT:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "success": False, 
                    "error": {"code": "BACKPRESSURE_REJECTION", "message": "System saturated. Try again later."}
                }
            )
        
        BackpressureMiddleware.active_requests += 1
        try:
            return await call_next(request)
        finally:
            BackpressureMiddleware.active_requests -= 1
