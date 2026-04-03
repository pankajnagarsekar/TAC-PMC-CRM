import sys
import os
import json
from datetime import datetime, timedelta

# Add the app directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.modules.scheduler.calculate_critical_path import run_calculation

def debug_cpm():
    project_start = "2026-04-01"
    tasks = [
        {"task_id": "T11", "task_name": "MSO Task", "task_mode": "Auto", "duration": 4, "constraint_type": "MSO", "constraint_date": "2026-04-10"},
        {"task_id": "P1", "task_name": "Parent", "is_summary": True, "summary_type": "auto"},
        {"task_id": "C1", "task_name": "Child 1", "parent_id": "P1", "duration": 2, "predecessors": ["T11"]},
        {"task_id": "C2", "task_name": "Child 2", "parent_id": "P1", "duration": 4, "predecessors": ["C1"]}
    ]
    input_data = {"project_start": project_start, "tasks": tasks}
    result = run_calculation(input_data)
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return

    for t in result["tasks"]:
        if t["task_id"] in ["P1", "C1", "C2", "T11"]:
            print(f"Task {t['task_id']}: Start={t.get('scheduled_start')}, Finish={t.get('scheduled_finish')}")

if __name__ == "__main__":
    debug_cpm()
