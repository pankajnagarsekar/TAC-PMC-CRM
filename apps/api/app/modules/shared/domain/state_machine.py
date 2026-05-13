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
        "Approved": {"Processing", "Rejected", "Paid"},
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

    # TASK STATES
    TASK_TRANSITIONS: Dict[str, Set[str]] = {
        "Open": {"In Progress", "Closed"},
        "In Progress": {"Review", "Completed", "Open", "Closed"},
        "Review": {"Completed", "In Progress", "Closed"},
        "Completed": {"Review", "Closed"},
        "Closed": set(),  # FINAL: Data Freeze
    }

    # WORK ORDER STATES
    WORK_ORDER_TRANSITIONS: Dict[str, Set[str]] = {
        "Draft": {"Pending", "Cancelled"},
        "Pending": {"Approved", "Rejected", "Cancelled"},
        "Approved": {"Completed", "Cancelled"},
        "Completed": {"Closed"},
        "Closed": set(),  # FINAL: Data Freeze
        "Cancelled": set(),  # FINAL
        "Rejected": {"Draft", "Cancelled"},
    }

    # EDITABLE STATES (Where fields can be updated)
    EDITABLE_STATES: Dict[str, Set[str]] = {
        "PROJECT": {"Draft", "Active", "On-Hold"},
        "PAYMENT": {"Draft", "Rejected"},
        "DPR": {"Draft", "Rejected"},
        "TASK": {"Open", "In Progress", "Review", "Completed"},
        "WORK_ORDER": {"Draft", "Pending", "Rejected"},
    }

    @classmethod
    def validate_transition(cls, entity_type: str, current_state: str, next_state: str):
        """Standard validator for all transitions. Raises IllegalTransitionError or DataFreezeError."""
        if entity_type == "PROJECT":
            transitions = cls.PROJECT_TRANSITIONS
        elif entity_type == "DPR":
            transitions = cls.DPR_TRANSITIONS
        elif entity_type == "TASK":
            transitions = cls.TASK_TRANSITIONS
        elif entity_type == "WORK_ORDER":
            transitions = cls.WORK_ORDER_TRANSITIONS
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
        allowed_states = cls.EDITABLE_STATES.get(entity_type)
        if allowed_states is not None:
            if state not in allowed_states:
                raise DataFreezeError(entity_type, state)
            return True

        # Fallback to legacy 'no targets' logic if not explicitly defined in EDITABLE_STATES
        if entity_type == "PROJECT":
            transitions = cls.PROJECT_TRANSITIONS
        elif entity_type == "DPR":
            transitions = cls.DPR_TRANSITIONS
        elif entity_type == "TASK":
            transitions = cls.TASK_TRANSITIONS
        elif entity_type == "WORK_ORDER":
            transitions = cls.WORK_ORDER_TRANSITIONS
        else:
            transitions = cls.PAYMENT_TRANSITIONS

        if not transitions.get(state):  # If no targets, it's a frozen state
            raise DataFreezeError(entity_type, state)
        return True
