import json
import random
from datetime import datetime, timedelta
from bson import ObjectId

def generate_project(task_count=5000, dep_count=7000):
    project_id = str(ObjectId())
    tasks = []
    
    # 1. Generate Tasks
    start_date = datetime(2026, 1, 1).date()
    for i in range(task_count):
        task_id = str(ObjectId())
        duration = random.randint(1, 20)
        tasks.append({
            "task_id": task_id,
            "project_id": project_id,
            "task_name": f"Stress Task {i}",
            "task_mode": "Auto",
            "wbs_code": str(i + 1),
            "predecessors": [],
            "constraint_type": "ASAP",
            "constraint_date": None,
            "scheduled_start": (start_date + timedelta(days=random.randint(0, 365))).isoformat() if i == 0 else None,
            "scheduled_finish": None,
            "scheduled_duration": duration,
            "actual_start": None,
            "actual_finish": None,
            "percent_complete": 0,
            "is_milestone": (i % 50 == 0),
            "deadline": None,
            "parent_id": None,
            "is_summary": False,
            "summary_type": "auto",
            "assigned_resources": [],
            "baseline_cost": random.randint(1000, 100000),
            "wo_value": random.randint(1000, 100000),
        })

    # 2. Generate Dependencies (DAG-safe)
    current_deps = 0
    while current_deps < dep_count:
        idx_a = random.randint(0, task_count - 2)
        idx_b = random.randint(idx_a + 1, task_count - 1)
        
        exists = any(p["task_id"] == tasks[idx_a]["task_id"] for p in tasks[idx_b]["predecessors"])
        if not exists:
            tasks[idx_b]["predecessors"].append({
                "task_id": tasks[idx_a]["task_id"],
                "project_id": project_id,
                "type": "FS",
                "lag_days": 0,
                "is_external": False,
                "strength": "hard"
            })
            current_deps += 1

    return {
        "project_id": project_id,
        "calendar": {
            "work_days": [1, 2, 3, 4, 5, 6],
            "holidays": [],
            "shift_start": "09:00",
            "shift_end": "18:00"
        },
        "tasks": tasks
    }

if __name__ == "__main__":
    print(f"Generating large project (5k tasks, 7k deps)...")
    data = generate_project()
    with open("large_project_5k.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Done. Saved to large_project_5k.json")
