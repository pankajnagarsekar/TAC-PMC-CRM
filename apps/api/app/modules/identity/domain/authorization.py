from app.modules.shared.domain.exceptions import PermissionDeniedError

from .types import UserRole


class IdentityAuthorizationManager:
    """Centralised identity permission checks."""

    @staticmethod
    def verify_admin_role(user: dict) -> None:
        if user.get("role") != UserRole.ADMIN:
            raise PermissionDeniedError("Admin role required")

    @staticmethod
    def verify_self_or_admin(user: dict, target_user_id: str) -> None:
        """Allow if user is Admin OR accessing their own record."""
        if user.get("role") == UserRole.ADMIN:
            return
        if str(user.get("user_id")) == str(target_user_id):
            return
        raise PermissionDeniedError("Access denied: admin or self only")

    @staticmethod
    def verify_self(user: dict, target_user_id: str) -> None:
        if str(user.get("user_id")) != str(target_user_id):
            raise PermissionDeniedError("Access denied: own account only")
