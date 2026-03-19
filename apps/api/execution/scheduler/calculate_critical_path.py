from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional

def str_to_date(date_str: str) -> date:
    """DD-MM-YY to date object"""
    return datetime.strptime(date_str, "%d-%m-%y").date()

def date_to_str(d: date) -> str:
    """Date object to DD-MM-YY"""
    return d.strftime("%d-%m-%y")

def is_work_day(d: date) -> bool:
    """Sunday (index 6) is a holiday (Goa standard)"""
    return d.weekday() != 6

def get_finish_date(start: date, duration: int) -> date:
    """Calculate finish date for a duration of work days, inclusive of start_date"""
    if duration <= 0:
        return start
    
    current = start
    work_days_count = 0
    
    while True:
        if is_work_day(current):
            work_days_count += 1
            if work_days_count == duration:
                return current
        current += timedelta(days=1)

def get_next_start_day(finish: date) -> date:
    """Get the next work day after the finish date"""
    current = finish + timedelta(days=1)
    while not is_work_day(current):
        current += timedelta(days=1)
    return current

def calculate_critical_path(tasks: List[Dict[str, Any]], project_start_str: str) -> List[Dict[str, Any]]:
    """
    Implements Critical Path Method (CPM) for construction scheduling (6-day work week).
    Tasks: List[{ id, name, duration, predecessors: [id] }]
    project_start_str: "DD-MM-YY"
    """
    project_start = str_to_date(project_start_str)
    
    # Ensure start date is a work day
    while not is_work_day(project_start):
        project_start += timedelta(days=1)
    
    # 1. Forward Pass (Early Start, Early Finish)
    task_map = {t["id"]: {**t} for t in tasks}
    for tid in task_map:
        task_map[tid]["es"] = None
        task_map[tid]["ef"] = None
        task_map[tid]["successors"] = []
        
    for tid, t in task_map.items():
        for pid in t.get("predecessors", []):
            if pid in task_map:
                task_map[pid]["successors"].append(tid)

    # Simple topological sort/dependency order for forward pass
    def compute_ef(tid):
        if task_map[tid]["ef"] is not None:
            return task_map[tid]["ef"]
        
        preds = task_map[tid].get("predecessors", [])
        if not preds:
            es = project_start
        else:
            max_ef = None
            for pid in preds:
                p_ef = compute_ef(pid)
                if max_ef is None or p_ef > max_ef:
                    max_ef = p_ef
            es = get_next_start_day(max_ef)
        
        task_map[tid]["es"] = es
        task_map[tid]["ef"] = get_finish_date(es, task_map[tid]["duration"])
        return task_map[tid]["ef"]

    for tid in task_map:
        compute_ef(tid)

    # 2. Backward Pass (Late Start, Late Finish)
    # Find max finish date to start backward pass
    max_finish = max(t["ef"] for t in task_map.values())
    
    for tid in task_map:
        task_map[tid]["ls"] = None
        task_map[tid]["lf"] = None

    def get_prev_work_day(d: date) -> date:
        current = d - timedelta(days=1)
        while not is_work_day(current):
            current -= timedelta(days=1)
        return current

    def get_start_from_finish(finish: date, duration: int) -> date:
        if duration <= 0:
            return finish
        current = finish
        work_days_count = 0
        while True:
            if is_work_day(current):
                work_days_count += 1
                if work_days_count == duration:
                    return current
            current -= timedelta(days=1)

    def compute_ls(tid):
        if task_map[tid]["ls"] is not None:
            return task_map[tid]["ls"]
        
        succs = task_map[tid]["successors"]
        if not succs:
            lf = max_finish
        else:
            min_ls = None
            for sid in succs:
                s_ls = compute_ls(sid)
                if min_ls is None or s_ls < min_ls:
                    min_ls = s_ls
            lf = get_prev_work_day(min_ls)
        
        task_map[tid]["lf"] = lf
        task_map[tid]["ls"] = get_start_from_finish(lf, task_map[tid]["duration"])
        return task_map[tid]["ls"]

    for tid in task_map:
        compute_ls(tid)

    # 3. Slack & Critical Path Identification
    # Total slack (float) = LF - EF or LS - ES
    # Since date arithmetic on 6-day week is tricky, we compare work days.
    
    results = []
    for tid, t in task_map.items():
        # Using late finish minus early finish in work days would be complex.
        # But we can check if ES == LS
        is_critical = (t["es"] == t["ls"])
        
        results.append({
            "id": t["id"],
            "name": t["name"],
            "duration": t["duration"],
            "predecessors": t["predecessors"],
            "start": date_to_str(t["es"]),
            "finish": date_to_str(t["ef"]),
            "is_critical": is_critical
        })
        
    return results

if __name__ == "__main__":
    import json
    import sys
    
    # Read from stdin
    try:
        input_data = json.load(sys.stdin)
        tasks = input_data.get("tasks", [])
        project_start = input_data.get("project_start", "01-01-26")
        
        result = calculate_critical_path(tasks, project_start)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
