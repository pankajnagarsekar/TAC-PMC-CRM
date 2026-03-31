import json
import sys
from datetime import datetime, timedelta


def calculate_cpm():
    try:
        # 1. READ INPUT
        input_data = json.load(sys.stdin)
        tasks_input = input_data.get("tasks", [])
        project_start_str = input_data.get("project_start")

        if not project_start_str:
            project_start = datetime.now()
        else:
            try:
                # Handle YYYY-MM-DD or full ISO
                project_start = datetime.fromisoformat(
                    project_start_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                project_start = datetime.strptime(project_start_str[:10], "%Y-%m-%d")

        if not tasks_input:
            print(
                json.dumps({"tasks": [], "critical_path": [], "total_duration_days": 0})
            )
            return

        # 2. PREPARE DATA STRUCTURES
        task_map = {}
        for t in tasks_input:
            tid = str(t["task_id"])
            # Default missing fields
            task_map[tid] = {
                "task_id": tid,
                "duration": int(t.get("duration") or t.get("scheduled_duration") or 0),
                "dependencies": [str(d) for d in t.get("dependencies", [])],
                "predecessors": [
                    str(p.get("task_id") if isinstance(p, dict) else p)
                    for p in t.get("predecessors", [])
                ],
                "successors": [],
                "es": None,
                "ef": None,
                "ls": None,
                "lf": None,
                "slack": 0,
                "is_critical": False,
                "original": t,
            }
            # Unify dependencies and predecessors
            task_map[tid]["preds"] = list(
                set(task_map[tid]["dependencies"] + task_map[tid]["predecessors"])
            )

        # Build successors and in-degree
        in_degree = {tid: 0 for tid in task_map}
        for tid, task in task_map.items():
            for pred_id in task["preds"]:
                if pred_id in task_map:
                    task_map[pred_id]["successors"].append(tid)
                    in_degree[tid] += 1

        # 3. TOPOLOGICAL SORT (Kahn's Algorithm)
        queue = [tid for tid in in_degree if in_degree[tid] == 0]
        topo_order = []

        while queue:
            curr_id = queue.pop(0)
            topo_order.append(curr_id)
            for succ_id in task_map[curr_id]["successors"]:
                in_degree[succ_id] -= 1
                if in_degree[succ_id] == 0:
                    queue.append(succ_id)

        if len(topo_order) < len(task_map):
            print(
                json.dumps({"error": "Circular dependency detected in schedule graph."})
            )
            return

        # 4. FORWARD PASS
        for tid in topo_order:
            task = task_map[tid]
            if not task["preds"]:
                task["es"] = project_start
            else:
                max_ef = project_start
                for pred_id in task["preds"]:
                    if pred_id in task_map and task_map[pred_id]["ef"]:
                        if task_map[pred_id]["ef"] > max_ef:
                            max_ef = task_map[pred_id]["ef"]
                task["es"] = max_ef

            task["ef"] = task["es"] + timedelta(days=task["duration"])

        # 5. BACKWARD PASS
        final_ef = project_start
        if topo_order:
            final_ef = max(
                (task_map[tid]["ef"] for tid in task_map), default=project_start
            )

        for tid in reversed(topo_order):
            task = task_map[tid]
            if not task["successors"]:
                task["lf"] = final_ef
            else:
                min_ls = final_ef
                for succ_id in task["successors"]:
                    if succ_id in task_map and task_map[succ_id]["ls"]:
                        if task_map[succ_id]["ls"] < min_ls:
                            min_ls = task_map[succ_id]["ls"]
                task["lf"] = min_ls

            task["ls"] = task["lf"] - timedelta(days=task["duration"])
            task["slack"] = (task["ls"] - task["es"]).days
            task["is_critical"] = task["slack"] <= 0

        # 6. FORMAT OUTPUT
        output_tasks = []
        critical_path = []

        for tid in topo_order:
            t = task_map[tid]
            if t["is_critical"]:
                critical_path.append(tid)

            # Update the original task dict with calculated values
            updated = t["original"].copy()
            updated.update(
                {
                    "scheduled_start": t["es"].strftime("%Y-%m-%d"),
                    "scheduled_finish": t["ef"].strftime("%Y-%m-%d"),
                    "scheduled_duration": t["duration"],
                    "early_start": t["es"].strftime("%Y-%m-%d"),
                    "early_finish": t["ef"].strftime("%Y-%m-%d"),
                    "late_start": t["ls"].strftime("%Y-%m-%d"),
                    "late_finish": t["lf"].strftime("%Y-%m-%d"),
                    "total_slack": t["slack"],
                    "is_critical": t["is_critical"],
                }
            )
            output_tasks.append(updated)

        total_duration = (final_ef - project_start).days

        print(
            json.dumps(
                {
                    "tasks": output_tasks,
                    "critical_path": critical_path,
                    "total_duration_days": total_duration,
                    "status": "success",
                }
            )
        )

    except Exception as e:
        print(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    calculate_cpm()
