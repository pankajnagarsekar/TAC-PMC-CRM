from datetime import datetime, timezone

def now() -> datetime:
    """System Constitution: Unified Time Source (Point 65)"""
    return datetime.now(timezone.utc)

def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return now().isoformat()
