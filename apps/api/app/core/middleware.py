import asyncio
import logging
import time
import uuid
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)


class StandardResponseMiddleware(BaseHTTPMiddleware):
    """
    Sovereign Response Wrapper (Point 4, 10).
    Injects tracing metadata, enforces rate limits, and normalizes system faults.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            start_time = time.time()
            request_id = str(uuid.uuid4())

            # 1. RATE LIMIT ENFORCEMENT (Point 5, 116)
            try:
                client_host = getattr(request.client, "host", "anonymous") if request.client else "anonymous"
            except Exception:
                client_host = "anonymous"

            identity = request.headers.get("Authorization", client_host)

            # 2. PATH EXCLUSION CHECK
            if request.url.path not in ["/docs", "/redoc", "/openapi.json"]:
                try:
                    # Tier routing: PDF/Excel file downloads → Export (30/min)
                    # Report/analytics data endpoints → Heavy (200/min)
                    # Everything else → Standard (60/s)
                    path = request.url.path
                    if "export/pdf" in path or "export/excel" in path or "export-pdf" in path:
                        tier = "Export"
                    elif "export" in path or "report" in path:
                        tier = "Heavy"
                    else:
                        tier = "Standard"
                    await limiter.check(identity, tier=tier)
                except HTTPException as he:
                    return self._standard_error(
                        he.status_code, he.detail, request_id, start_time
                    )

            logger.info(f"REQUEST START: {request.method} {request.url.path} | ID: {request_id}")
            response = await call_next(request)
            logger.info(
                f"REQUEST END: {request.method} {request.url.path} | "
                f"Status: {response.status_code} | ID: {request_id}"
            )
            process_time = time.time() - start_time

            if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
                return response

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            return response

        except HTTPException as he:
            return self._standard_error(
                he.status_code, he.detail, request_id, start_time
            )

        except Exception as exc:
            from app.modules.shared.domain.exceptions import DomainError, ValidationError
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_msg = "A critical system fault occurred."

            if isinstance(exc, ValidationError):
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                error_msg = str(exc)
            elif isinstance(exc, DomainError):
                status_code = status.HTTP_400_BAD_REQUEST
                error_msg = str(exc)
            elif isinstance(exc, HTTPException):
                status_code = exc.status_code
                error_msg = exc.detail
            else:
                import traceback
                print(f"CRITICAL ERROR: {exc}")
                traceback.print_exc()
                logger.error(f"SYSTEM_FAULT: {exc} | ID: {request_id}", exc_info=True)
                error_msg = f"SYSTEM_FAULT: {str(exc)}"

            logger.error(f"API_ERROR: {error_msg} | Path: {request.url.path} | ID: {request_id}")
            return self._standard_error(
                status_code,
                error_msg,
                request_id,
                start_time,
             )

    def _standard_error(
        self, code: int, message: Any, request_id: str, start_time: float
    ):
        process_time = time.time() - start_time

        # Normalize code to string for better DX (BUG-10)
        error_code = "SYSTEM_FAULT"
        if code == 429:
            error_code = "RATE_LIMIT_EXCEEDED"
        elif code == 503:
            error_code = "SERVICE_UNAVAILABLE"
        elif code == 400:
            error_code = "BAD_REQUEST"
        elif code == 401:
            error_code = "UNAUTHORIZED"
        elif code == 403:
            error_code = "FORBIDDEN"
        elif code == 404:
            error_code = "NOT_FOUND"

        return JSONResponse(
            status_code=code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message,
                    "request_id": request_id,
                    "status": code
                },
                "meta": {"process_time": process_time},
            },
        )


class BackpressureMiddleware(BaseHTTPMiddleware):
    """
    Saturation Guard (Point 105).
    Immediate rejection when system concurrency limit is reached.
    """

    MAX_CONCURRENT = 200
    _semaphore = None

    @classmethod
    def get_semaphore(cls):
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(cls.MAX_CONCURRENT)
        return cls._semaphore

    async def dispatch(self, request: Request, call_next):
        sem = self.get_semaphore()
        logger.debug(f"BACKPRESSURE: checking {request.url.path} | Sem Locked: {sem.locked()}")
        if sem.locked():
            logger.debug("BACKPRESSURE: DETECTED LOCK - returning 503")
            logger.warning(
                f"BACKPRESSURE_REJECTION: System saturated at {self.MAX_CONCURRENT} "
                f"concurrent requests. Path: {request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "success": False,
                    "error": {
                        "code": "BACKPRESSURE_REJECTION",
                        "message": "System saturated. Try again later.",
                    },
                },
            )

        logger.debug("BACKPRESSURE: PASSED - acquiring semaphore")
        async with sem:
            return await call_next(request)
