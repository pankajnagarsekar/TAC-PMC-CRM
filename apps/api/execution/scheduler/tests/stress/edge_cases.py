import sys
import os
from datetime import date

# Add apps/api to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from execution.scheduler.engine.interfaces import (
    CalculationRequest, EngineCalendar, TaskInput, PredecessorInput
)
from execution.scheduler.engine.calculate_critical_path import calculate_critical_path
from execution.scheduler.engine.dag_validator import validate_dag

def create_base_request(tasks):
    calendar = EngineCalendar(work_days=[1,2,3,4,5], holidays=[])
    return CalculationRequest(project_id="test", calendar=calendar, tasks=tasks)

def test_circular():
    print("\nTest Case: Circular Dependency (A -> B -> A)")
    t1 = TaskInput(task_id="A", task_mode="Auto", predecessors=[PredecessorInput(task_id="B", project_id=None)], 
                   constraint_type="ASAP", constraint_date=None, scheduled_start=None, 
                   scheduled_finish=None, scheduled_duration=5, actual_start=None, 
                   actual_finish=None, percent_complete=0, is_milestone=False, 
                   deadline=None, parent_id=None, is_summary=False, summary_type="auto", 
                   assigned_resources=[])
    
    t2 = TaskInput(task_id="B", task_mode="Auto", predecessors=[PredecessorInput(task_id="A", project_id=None)], 
                   constraint_type="ASAP", constraint_date=None, scheduled_start=None, 
                   scheduled_finish=None, scheduled_duration=5, actual_start=None, 
                   actual_finish=None, percent_complete=0, is_milestone=False, 
                   deadline=None, parent_id=None, is_summary=False, summary_type="auto", 
                   assigned_resources=[])

    req = create_base_request([t1, t2])
    result = validate_dag(req)
    print(f"Is Valid: {result.is_valid}")
    print(f"Error: {result.error_message}")
    assert not result.is_valid

def test_deep_chain():
    print("\nTest Case: Deep Chain (100 links)")
    tasks = []
    for i in range(100):
        preds = []
        if i > 0:
            preds = [PredecessorInput(task_id=str(i-1), project_id=None)]
        
        t = TaskInput(task_id=str(i), task_mode="Auto", predecessors=preds, 
                     constraint_type="ASAP", constraint_date=None, 
                     scheduled_start=date(2026,1,1) if i == 0 else None, 
                     scheduled_finish=None, scheduled_duration=1, actual_start=None, 
                     actual_finish=None, percent_complete=0, is_milestone=False, 
                     deadline=None, parent_id=None, is_summary=False, summary_type="auto", 
                     assigned_resources=[])
        tasks.append(t)

    req = create_base_request(tasks)
    response = calculate_critical_path(req)
    print(f"Status: {response.status}")
    print(f"Final Task Finish: {response.tasks[-1].scheduled_finish}")
    assert response.status == "success"

def test_constraints():
    print("\nTest Case: MSO (Must Start On) Constraint")
    mso_date = date(2026, 6, 1)
    t1 = TaskInput(task_id="MSO_TASK", task_mode="Auto", predecessors=[], 
                   constraint_type="MSO", constraint_date=mso_date, 
                   scheduled_start=None, scheduled_finish=None, scheduled_duration=5, 
                   actual_start=None, actual_finish=None, percent_complete=0, 
                   is_milestone=False, deadline=None, parent_id=None, is_summary=False, 
                   summary_type="auto", assigned_resources=[])

    req = create_base_request([t1])
    response = calculate_critical_path(req)
    print(f"Task Start: {response.tasks[0].scheduled_start}")
    assert response.tasks[0].scheduled_start == mso_date

if __name__ == "__main__":
    test_circular()
    test_deep_chain()
    test_constraints()
    print("\nAll edge cases PASSED.")
