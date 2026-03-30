from typing import Dict, Set

from .exceptions import DataFreezeError, IllegalTransitionError


class StateMachine:
    """
    Sovereign State Machine for all entity transitions.
    Enforces 'Data Freeze' for immutable states via Domain Exceptions.
    """

    # PROJECT STATES
    PROJECT_TRANSITIONS: Dict[str, Set[str]] = {
        "Draft": {"Active", "Cancelled"},
        "Active": {"On-Hold", "Completed", "Cancelled"},
        "On-Hold": {"Active", "Cancelled"},
        "Completed": set(),  # FINAL: Data Freeze
        "Cancelled": set(),  # FINAL
    }

    # PAYMENT STATES
    PAYMENT_TRANSITIONS: Dict[str, Set[str]] = {
        "Draft": {"Submitted", "Cancelled"},
        "Submitted": {"Approved", "Rejected", "Cancelled"},
        "Approved": {"Processing", "Rejected"},
        "Processing": {"Paid", "Failed"},
        "Rejected": {"Draft", "Cancelled"},
        "Paid": set(),  # FINAL
        "Cancelled": set(),  # FINAL
    }

    # DPR STATES
    DPR_TRANSITIONS: Dict[str, Set[str]] = {
        "Draft": {"Submitted", "Cancelled"},
        "Submitted": {"Approved", "Rejected"},
        "Approved": set(),  # FINAL
        "Rejected": {"Draft", "Cancelled"},
        "Cancelled": set(),
    }

    @classmethod
    def validate_transition(cls, entity_type: str, current_state: str, next_state: str):
        """Standard validator for all transitions. Raises IllegalTransitionError or DataFreezeError."""
        if entity_type == "PROJECT":
            transitions = cls.PROJECT_TRANSITIONS
        elif entity_type == "DPR":
            transitions = cls.DPR_TRANSITIONS
        else:
            transitions = cls.PAYMENT_TRANSITIONS

        if current_state not in transitions:
            # This is still a data-integrity check of sorts, keeping it generic
            raise ValueError(f"Unknown state '{current_state}' for {entity_type}")

        # Hard check for final states (Data Freeze)
        if not transitions[current_state] and next_state != current_state:
            raise DataFreezeError(entity_type, current_state)

        if next_state not in transitions[current_state] and next_state != current_state:
            allowed = list(transitions[current_state])
            raise IllegalTransitionError(
                entity_type, current_state, next_state, allowed
            )

        return True

    @classmethod
    def check_modification_allowed(cls, entity_type: str, state: str):
        """Verify if fields can be updated in current state. Raises DataFreezeError if frozen."""
        if entity_type == "PROJECT":
            transitions = cls.PROJECT_TRANSITIONS
        elif entity_type == "DPR":
            transitions = cls.DPR_TRANSITIONS
        else:
            transitions = cls.PAYMENT_TRANSITIONS

        if not transitions.get(state):  # If no targets, it's a frozen state
            raise DataFreezeError(entity_type, state)
        return True
