from enum import Enum
from typing import Dict


class UserRole(str, Enum):
    ADMIN = "Admin"
    SUPERVISOR = "Supervisor"
    OTHER = "Other"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


# Role hierarchy: higher index = more permissions
USER_ROLE_HIERARCHY: Dict[str, int] = {
    UserRole.OTHER: 0,
    UserRole.SUPERVISOR: 1,
    UserRole.ADMIN: 2,
}


def role_gte(role: str, required: str) -> bool:
    """Return True if role has >= permissions than required."""
    return USER_ROLE_HIERARCHY.get(role, 0) >= USER_ROLE_HIERARCHY.get(required, 0)
