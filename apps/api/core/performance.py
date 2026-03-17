"""
Performance Benchmarking Utilities
Implements Phase 6.5.3 - Target benchmarks:
- WO Save < 200ms
- PC Close < 200ms
- Petty Entry < 100ms
- Report gen < 2s
"""

import time
import logging
from functools import wraps
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

PERFORMANCE_BENCHMARKS = {
    "WORK_ORDER_SAVE": 200,          # ms
    "PAYMENT_CERTIFICATE_CLOSE": 200, # ms
    "PETTY_CASH_ENTRY": 100,         # ms
    "REPORT_GENERATION": 2000,        # ms
}

PerformanceLog: list[dict] = []


def measure_performance(operation: str):
    """
    Decorator to measure and log performance against benchmarks.
    
    Usage:
        @measure_performance("WORK_ORDER_SAVE")
        async def create_work_order(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _log_performance(operation, duration_ms)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _log_performance(operation, duration_ms)
        
        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def _log_performance(operation: str, duration_ms: float) -> None:
    """Internal function to log performance metrics"""
    target_ms = PERFORMANCE_BENCHMARKS.get(operation, 0)
    passed = duration_ms <= target_ms
    
    metrics = {
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "target_ms": target_ms,
        "passed": passed,
    }
    
    PerformanceLog.append(metrics)
    
    if passed:
        logger.info(f"[PERF] {operation}: {metrics['duration_ms']}ms ✓ (target: {target_ms}ms)")
    else:
        logger.warning(f"[PERF] {operation}: {metrics['duration_ms']}ms ✗ (target: {target_ms}ms) - SLOW")


def get_performance_history(operation: Optional[str] = None) -> list[dict]:
    """Get performance history for an operation or all operations"""
    if operation:
        return [m for m in PerformanceLog if m["operation"] == operation]
    return list(PerformanceLog)


def get_average_performance(operation: str) -> dict:
    """Get average performance for an operation"""
    history = get_performance_history(operation)
    if not history:
        return {"avg_ms": 0, "pass_rate": 0}
    
    avg_ms = sum(m["duration_ms"] for m in history) / len(history)
    passed_count = sum(1 for m in history if m["passed"])
    pass_rate = (passed_count / len(history)) * 100
    
    return {
        "avg_ms": round(avg_ms, 2),
        "pass_rate": round(pass_rate, 1)
    }


def clear_performance_history() -> None:
    """Clear performance history"""
    PerformanceLog.clear()
