from typing import Set, Dict, List
from fastapi import HTTPException

class StateMachine:
    """
    Sovereign State Machine for all entity transitions (Point 31, 87, 94).
    Enforces 'Data Freeze' for immutable states and 'Fail Fast' on illegal jumps.
    """
    
    # PROJECT STATES (Point 31)
    PROJECT_TRANSITIONS: Dict[str, Set[str]] = {
        "Draft": {"Active", "Cancelled"},
        "Active": {"On-Hold", "Completed", "Cancelled"},
        "On-Hold": {"Active", "Cancelled"},
        "Completed": set(), # FINAL: Data Freeze (Point 87)
        "Cancelled": set()  # FINAL
    }

    # PAYMENT STATES
    PAYMENT_TRANSITIONS: Dict[str, Set[str]] = {
        "Draft": {"Submitted", "Cancelled"},
        "Submitted": {"Approved", "Rejected", "Cancelled"},
        "Approved": {"Processing", "Rejected"},
        "Processing": {"Paid", "Failed"},
        "Rejected": {"Draft", "Cancelled"},
        "Paid": set(),    # FINAL
        "Cancelled": set() # FINAL
    }

    @classmethod
    def validate_transition(cls, entity_type: str, current_state: str, next_state: str):
        """Standard validator for all transitions. Fail fast if illegal (Point 94)"""
        transitions = cls.PROJECT_TRANSITIONS if entity_type == "PROJECT" else cls.PAYMENT_TRANSITIONS
        
        if current_state not in transitions:
            raise HTTPException(status_code=400, detail=f"DOMAIN_ERROR: Unknown state '{current_state}' for {entity_type}")
            
        # Hard check for final states (Data Freeze - Point 87)
        if not transitions[current_state] and next_state != current_state:
             raise HTTPException(
                 status_code=403, 
                 detail=f"STATE_FREEZE: Entity is in final state '{current_state}' and cannot be modified."
             )

        if next_state not in transitions[current_state] and next_state != current_state:
            allowed = ", ".join(transitions[current_state])
            raise HTTPException(
                status_code=400, 
                detail=f"ILLEGAL_TRANSITION: Cannot move {entity_type} from {current_state} to {next_state}. Allowed: [{allowed}]"
            )
        
        return True

    @classmethod
    def check_modification_allowed(cls, entity_type: str, state: str):
        """Verify if fields can be updated in current state (Point 87)"""
        transitions = cls.PROJECT_TRANSITIONS if entity_type == "PROJECT" else cls.PAYMENT_TRANSITIONS
        if not transitions.get(state): # If no targets, it's a frozen state
            raise HTTPException(
                 status_code=403, 
                 detail=f"DOMAIN_ERROR: Modification blocked. {entity_type} is '{state}'."
            )
        return True
