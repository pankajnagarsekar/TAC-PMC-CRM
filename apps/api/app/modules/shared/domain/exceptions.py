from typing import Optional


class DomainError(Exception):
    """Base class for all domain-related errors."""

    def __init__(self, message: str, entity_id: Optional[str] = None):
        self.message = message
        self.entity_id = entity_id
        super().__init__(self.message)


class IllegalTransitionError(DomainError):
    """Raised when an entity tries to move to a forbidden state."""

    def __init__(
        self,
        entity_type: str,
        current_state: str,
        next_state: str,
        allowed: Optional[list] = None,
    ):
        msg = f"Cannot move {entity_type} from {current_state} to {next_state}."
        if allowed:
            msg += f" Allowed: [{', '.join(allowed)}]"
        super().__init__(msg)


class DataFreezeError(DomainError):
    """Raised when trying to modify an entity in a final/frozen state."""

    def __init__(self, entity_type: str, state: str):
        super().__init__(
            f"Entity {entity_type} is in final state '{state}' and cannot be modified."
        )


class FinancialIntegrityError(DomainError):
    """Raised when financial calculations or checksums fail integrity checks."""

    pass


class NotFoundError(DomainError):
    """Raised when an entity is not found (Replaces 404)."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(f"{entity_type} with ID {entity_id} not found.", entity_id)


class PermissionDeniedError(DomainError):
    """Raised when an operation is forbidden (Replaces 403)."""

    pass


class ValidationError(DomainError):
    """Raised when input validation fails in domain logic (Replaces 400)."""

    pass


class AuthenticationError(DomainError):
    """Raised when authentication fails or token is invalid (Replaces 401)."""

    pass
