import pytest
from app.modules.shared.domain.state_machine import StateMachine
from app.modules.shared.domain.exceptions import DataFreezeError, IllegalTransitionError

def test_task_valid_transition():
    # Open target scenarios
    assert StateMachine.validate_transition("TASK", "Open", "In Progress") is True
    assert StateMachine.validate_transition("TASK", "Open", "Closed") is True
    
    # In progress target scenarios
    assert StateMachine.validate_transition("TASK", "In Progress", "Review") is True
    
    # Review scenarios
    assert StateMachine.validate_transition("TASK", "Review", "Completed") is True

def test_task_invalid_transition():
    with pytest.raises(IllegalTransitionError):
        StateMachine.validate_transition("TASK", "Open", "Completed")
    
    with pytest.raises(IllegalTransitionError):
        StateMachine.validate_transition("TASK", "Review", "Open")

def test_task_data_freeze():
    assert StateMachine.check_modification_allowed("TASK", "Open") is True
    assert StateMachine.check_modification_allowed("TASK", "Completed") is True
    
    with pytest.raises(DataFreezeError):
        StateMachine.check_modification_allowed("TASK", "Closed")
    
    with pytest.raises(DataFreezeError):
        StateMachine.validate_transition("TASK", "Closed", "Open")
