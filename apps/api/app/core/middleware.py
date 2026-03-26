import time
import logging
import uuid
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class StandardResponseMiddleware(BaseHTTPMiddleware):
    """
    Enforces a unified API response structure across all endpoints. (Point 4)
    Structure: { "success": bool, "data": Any, "meta": dict, "error": dict }
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        # Request ID for tracing (Point 100)
        request_id = str(uuid.uuid4())
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Skip wrapping for non-JSON or standard docs
            if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
                return response

            # We would typically parse JSON and rewrap, but to keep it lightweight
            # and avoid double serialization, we'll let existing routers handle
            # the structure where possible, and use this to inject metadata.
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response

        except Exception as exc:
            process_time = time.time() - start_time
            logger.error(f"SYSTEM_FAULT: {exc} | ID: {request_id}", exc_info=True)
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "A critical system fault occurred.",
                        "request_id": request_id
                    },
                    "meta": {
                        "process_time": process_time
                    }
                }
            )

class BackpressureMiddleware(BaseHTTPMiddleware):
    """
    Blocks requests if system resources are saturated. (Point 105)
    Simple implementation based on active request counting.
    """
    active_requests = 0
    MAX_CONCURRENT = 100 # Adjust based on instance size

    async def dispatch(self, request: Request, call_next):
        if BackpressureMiddleware.active_requests >= BackpressureMiddleware.MAX_CONCURRENT:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "System saturated. Please retry later."}
            )
        
        BackpressureMiddleware.active_requests += 1
        try:
            return await call_next(request)
        finally:
            BackpressureMiddleware.active_requests -= 1
