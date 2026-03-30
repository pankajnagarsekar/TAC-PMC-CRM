import asyncio
import logging
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ConcurrencyManager:
    """
    Sovereign Concurrency Hub (Point 112, 125).
    Safeguards the event loop from CPU-bound tasks like AI summaries or PDF generation.
    """

    def __init__(self):
        # AI/Heavy logic process pool (Dedicated)
        cpu_count = os.cpu_count() or 2
        self.heavy_pool = ProcessPoolExecutor(
            max_workers=max(1, cpu_count - 1),
            mp_context=multiprocessing.get_context("spawn"),
        )

        # IO/External logic thread pool
        self.io_pool = ThreadPoolExecutor(max_workers=20)

        logger.info(f"CONCURRENCY_HUB: Initialized with {cpu_count} cores.")

    async def run_heavy(self, func, *args):
        """Execute CPU-bound logic in isolated process (Point 112)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.heavy_pool, func, *args)

    async def run_io(self, func, *args):
        """Execute blocking IO in thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.io_pool, func, *args)


# GLOBAL SINGLETON
concurrency_hub = ConcurrencyManager()
