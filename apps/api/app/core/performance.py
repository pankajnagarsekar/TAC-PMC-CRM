import logging
import time
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

PERFORMANCE_BENCHMARKS = {
    "WORK_ORDER_SAVE": 200,
    "PAYMENT_CERTIFICATE_CLOSE": 200,
    "PETTY_CASH_ENTRY": 100,
    "REPORT_GENERATION": 2000,
}


def measure_performance(operation: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                target_ms = PERFORMANCE_BENCHMARKS.get(operation, 0)
                if duration_ms > target_ms:
                    logger.warning(
                        f"[PERF] {operation} SLOW: {duration_ms:.2f}ms (target: {target_ms}ms)"
                    )
                else:
                    logger.info(f"[PERF] {operation}: {duration_ms:.2f}ms")

        return wrapper

    return decorator
