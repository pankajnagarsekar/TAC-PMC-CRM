import json
import time
import sys
import os
from datetime import date

# Add apps/api to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from execution.scheduler.engine.interfaces import (
    CalculationRequest, EngineCalendar, TaskInput, PredecessorInput
)
from execution.scheduler.engine.calculate_critical_path import calculate_critical_path

def parse_date(d_str):
    if not d_str: return None
    return date.fromisoformat(d_str.split('T')[0])

def run_benchmark():
    if not os.path.exists("large_project_5k.json"):
        print("Error: large_project_5k.json not found. Run generate_large_project.py first.")
        return

    with open("large_project_5k.json", "r") as f:
        data = json.load(f)

    # Convert to dataclasses
    calendar = EngineCalendar(
        work_days=data["calendar"]["work_days"],
        holidays=[parse_date(h) for h in data["calendar"]["holidays"]]
    )

    tasks = []
    for t in data["tasks"]:
        preds = [PredecessorInput(**p) for p in t["predecessors"]]
        
        # Filter fields for TaskInput dataclass
        task_input = TaskInput(
            task_id=t["task_id"],
            task_mode=t["task_mode"],
            predecessors=preds,
            constraint_type=t["constraint_type"],
            constraint_date=parse_date(t["constraint_date"]),
            scheduled_start=parse_date(t["scheduled_start"]),
            scheduled_finish=parse_date(t["scheduled_finish"]),
            scheduled_duration=t["scheduled_duration"],
            actual_start=parse_date(t["actual_start"]),
            actual_finish=parse_date(t["actual_finish"]),
            percent_complete=t["percent_complete"],
            is_milestone=t["is_milestone"],
            deadline=parse_date(t["deadline"]),
            parent_id=t["parent_id"],
            is_summary=t["is_summary"],
            summary_type=t["summary_type"],
            assigned_resources=t["assigned_resources"]
        )
        tasks.append(task_input)

    request = CalculationRequest(
        project_id=data["project_id"],
        calendar=calendar,
        tasks=tasks
    )

    print(f"Starting benchmark for {len(tasks)} tasks...")
    start_time = time.time()
    
    response = calculate_critical_path(request)
    
    end_time = time.time()
    duration = end_time - start_time

    print(f"Benchmark Completed.")
    print(f"Time Taken: {duration:.4f} seconds")
    print(f"Status: {response.status}")
    print(f"Tasks Calculated: {len(response.tasks)}")
    print(f"Critical Path Length: {len(response.critical_path)}")
    
    if duration < 5.0:
        print("PASS: Performance is within Constitution limits (< 5s).")
    else:
        print("FAIL: Performance exceeds Constitution limits.")

if __name__ == "__main__":
    run_benchmark()
