from typing import Optional, Any

class DomainError(Exception):
    """Base class for all domain-related errors."""
    def __init__(self, message: str, entity_id: Optional[str] = None):
        self.message = message
        self.entity_id = entity_id
        super().__init__(self.message)

class IllegalTransitionError(DomainError):
    """Raised when an entity tries to move to a forbidden state."""
    def __init__(self, entity_type: str, current_state: str, next_state: str, allowed: Optional[list] = None):
        msg = f"Cannot move {entity_type} from {current_state} to {next_state}."
        if allowed:
            msg += f" Allowed: [{', '.join(allowed)}]"
        super().__init__(msg)

class DataFreezeError(DomainError):
    """Raised when trying to modify an entity in a final/frozen state."""
    def __init__(self, entity_type: str, state: str):
        super().__init__(f"Entity {entity_type} is in final state '{state}' and cannot be modified.")

class FinancialIntegrityError(DomainError):
    """Raised when financial calculations or checksums fail integrity checks."""
    pass
