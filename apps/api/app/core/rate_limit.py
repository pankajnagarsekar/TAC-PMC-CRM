import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, status


class RateLimiter:
    """
    Tiered Traffic Controller (Point 5, 116).
    Enforces operational boundaries per user/identity.
    """

    def __init__(self):
        # In-memory store: {user_id: (count, reset_time)}
        self.buckets: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

        # TIERS (Point 5)
        self.TIERS = {
            "Standard": {"rate": 10, "window": 1.0},
            "Heavy": {"rate": 1, "window": 5.0},  # For exports/reports
            "Admin": {"rate": 100, "window": 1.0},
        }

    async def check(self, identity: str, tier: str = "Standard"):
        now = time.time()
        conf = self.TIERS.get(tier, self.TIERS["Standard"])

        count, reset_time = self.buckets[identity]

        if now > reset_time:
            # RESET BUCKET
            self.buckets[identity] = (1, now + conf["window"])
            return True

        if count >= conf["rate"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"RATE_LIMIT_EXCEEDED: Maximum {conf['rate']} requests per {conf['window']}s.",
            )

        self.buckets[identity] = (count + 1, reset_time)
        return True


# GLOBAL SINGLETON (In-memory)
limiter = RateLimiter()
