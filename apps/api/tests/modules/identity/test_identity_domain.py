"""Track E: Identity domain unit tests — types, authorization, exceptions."""
import pytest

from app.modules.identity.domain.authorization import IdentityAuthorizationManager
from app.modules.identity.domain.exceptions import (
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    PasswordTooWeakError,
    SelfDeactivationError,
    UserNotFoundError,
)
from app.modules.identity.domain.types import USER_ROLE_HIERARCHY, UserRole, role_gte
from app.modules.shared.domain.exceptions import PermissionDeniedError


def test_user_role_enum_values():
    assert UserRole.ADMIN == "Admin"
    assert UserRole.SUPERVISOR == "Supervisor"
    assert UserRole.OTHER == "Other"


def test_role_hierarchy_admin_highest():
    assert USER_ROLE_HIERARCHY[UserRole.ADMIN] > USER_ROLE_HIERARCHY[UserRole.SUPERVISOR]
    assert USER_ROLE_HIERARCHY[UserRole.SUPERVISOR] > USER_ROLE_HIERARCHY[UserRole.OTHER]


def test_role_gte():
    assert role_gte("Admin", "Supervisor") is True
    assert role_gte("Supervisor", "Admin") is False
    assert role_gte("Admin", "Admin") is True


def test_authorization_manager_admin_passes():
    user = {"role": "Admin", "user_id": "abc"}
    IdentityAuthorizationManager.verify_admin_role(user)  # should not raise


def test_authorization_manager_non_admin_raises():
    user = {"role": "Supervisor", "user_id": "abc"}
    with pytest.raises(PermissionDeniedError):
        IdentityAuthorizationManager.verify_admin_role(user)


def test_authorization_self_or_admin_self_passes():
    user = {"role": "Supervisor", "user_id": "user-1"}
    IdentityAuthorizationManager.verify_self_or_admin(user, "user-1")  # own record


def test_authorization_self_or_admin_other_blocked():
    user = {"role": "Supervisor", "user_id": "user-1"}
    with pytest.raises(PermissionDeniedError):
        IdentityAuthorizationManager.verify_self_or_admin(user, "user-2")


def test_exceptions_instantiate():
    assert "User" in str(UserNotFoundError("id123"))
    assert "Email" in str(EmailAlreadyExistsError("x@x.com"))
    assert "Password" in str(PasswordTooWeakError())
    assert "permissions" in str(InsufficientPermissionsError("delete"))
    assert "deactivate" in str(SelfDeactivationError("id1")).lower()
