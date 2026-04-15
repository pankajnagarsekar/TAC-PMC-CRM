from app.modules.shared.domain.exceptions import DomainError, NotFoundError, ValidationError


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: str):
        super().__init__("User", user_id)


class EmailAlreadyExistsError(ValidationError):
    def __init__(self, email: str):
        super().__init__(f"Email already registered: {email}")


class PasswordTooWeakError(ValidationError):
    def __init__(self):
        super().__init__(
            "Password must be at least 8 characters with 1 uppercase letter and 1 digit"
        )


class InsufficientPermissionsError(DomainError):
    def __init__(self, action: str):
        super().__init__(f"Insufficient permissions for: {action}")


class SelfDeactivationError(DomainError):
    def __init__(self, user_id: str):
        super().__init__("Cannot deactivate yourself", entity_id=user_id)
