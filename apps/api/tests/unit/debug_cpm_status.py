import sys
import os


# Add the app directory to sys.path
sys.path.append(os.getcwd())

from app.modules.scheduler.calculate_critical_path import run_calculation  # noqa: E402


def debug_cpm_status():
    project_start = "2026-04-01"
    tasks = [
        {"task_id": "D1", "task_name": "Draft Task", "task_status": "draft", "duration": 1}
    ]
    input_data = {"project_start": project_start, "tasks": tasks}
    result = run_calculation(input_data)

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return

    for t in result["tasks"]:
        if t["task_id"] == "D1":
            print(f"Task {t['task_id']}: Status={t.get('task_status')}")


if __name__ == "__main__":
    debug_cpm_status()
