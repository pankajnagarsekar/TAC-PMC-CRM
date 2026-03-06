from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

# Initialize limiter
# Storing in Redis if REDIS_URL is present, otherwise in-memory
redis_url = os.getenv("REDIS_URL")
if redis_url:
    limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)
else:
    limiter = Limiter(key_func=get_remote_address)

def init_rate_limiting(app):
    """Register rate limit handler with the FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
