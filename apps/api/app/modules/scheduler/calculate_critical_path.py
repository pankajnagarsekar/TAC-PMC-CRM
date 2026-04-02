import json
import re
import sys
import uuid
from datetime import datetime, timedelta


def _parse_date(date_str):
    """Parse a date string to datetime. Returns None if invalid."""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    for fmt in ["%Y-%m-%d", "%d %m %Y", "%d-%m-%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(
                str(date_str)[:10].replace("/", "-").replace(" ", "-"),
                fmt.replace("/", "-").replace(" ", "-"),
            )
        except Exception:
            continue
    try:
        return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
    except Exception:
        return None


def _apply_constraint(es, ef, duration, constraint_type, constraint_date):
    """
    Apply constraint type to (es, ef) pair.
    Returns adjusted (es, ef).
    """
    if not constraint_type or constraint_type == "ASAP":
        return es, ef

    cd = _parse_date(constraint_date)
    if not cd:
        return es, ef

    ct = constraint_type.upper()

    if ct == "ALAP":
        # As Late As Possible — handled at backward pass level; skip here
        return es, ef
    elif ct == "SNET":
        # Start No Earlier Than: ES = max(ES, constraint_date)
        if es < cd:
            es = cd
            ef = es + timedelta(days=duration)
    elif ct == "SNLT":
        # Start No Later Than: ES = min(ES, constraint_date)
        if es > cd:
            es = cd
            ef = es + timedelta(days=duration)
    elif ct == "FNET":
        # Finish No Earlier Than: EF = max(EF, constraint_date)
        if ef < cd:
            ef = cd
            es = ef - timedelta(days=duration)
    elif ct == "FNLT":
        # Finish No Later Than: EF = min(EF, constraint_date)
        if ef > cd:
            ef = cd
            es = ef - timedelta(days=duration)
    elif ct == "MSO":
        # Must Start On
        es = cd
        ef = es + timedelta(days=duration)
    elif ct == "MFO":
        # Must Finish On
        ef = cd
        es = ef - timedelta(days=duration)

    return es, ef


def _compute_es_from_predecessors(task_id, task_map, project_start):
    """
    Compute ES for a task based on its predecessors using FS/SS/FF/SF + lag.
    Returns the minimum allowed ES datetime.
    """
    task = task_map[task_id]
    if not task["preds_full"]:
        return project_start

    max_es = project_start
    for pred_entry in task["preds_full"]:
        pred_id = pred_entry["task_id"]
        if pred_id not in task_map:
            continue
        pred = task_map[pred_id]
        link_type = pred_entry.get("type", "FS").upper()
        lag = int(pred_entry.get("lag_days", 0) or 0)

        pred_es = pred.get("es")
        pred_ef = pred.get("ef")
        if pred_es is None or pred_ef is None:
            continue

        if link_type == "FS":
            # Successor starts after predecessor finishes
            candidate = pred_ef + timedelta(days=lag)
        elif link_type == "SS":
            # Successor starts after predecessor starts
            candidate = pred_es + timedelta(days=lag)
        elif link_type == "FF":
            # Successor finishes after predecessor finishes
            # ES = pred_ef + lag - task_duration
            duration = task_map[task_id]["duration"]
            candidate = pred_ef + timedelta(days=lag) - timedelta(days=duration)
        elif link_type == "SF":
            # Successor finishes after predecessor starts
            duration = task_map[task_id]["duration"]
            candidate = pred_es + timedelta(days=lag) - timedelta(days=duration)
        else:
            # Default to FS
            candidate = pred_ef + timedelta(days=lag)

        if candidate > max_es:
            max_es = candidate

    return max_es


def run_calculation(input_data: dict) -> dict:
    """Core calculation logic (Importable). Implements the full 8-step CPM pipeline."""
    try:
        tasks_input = input_data.get("tasks", [])
        project_start_str = input_data.get("project_start")

        # 1. PARSE PROJECT START DATE
        if not project_start_str:
            project_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            project_start = _parse_date(project_start_str)
            if not project_start:
                project_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if not tasks_input:
            return {"tasks": [], "critical_path": [], "total_duration_days": 0}

        # 2. PREPARE DATA STRUCTURES
        task_map = {}
        for t in tasks_input:
            if not t.get("task_id"):
                continue
            tid = str(t["task_id"])

            raw_dur = t.get("duration") or t.get("scheduled_duration") or 0
            if isinstance(raw_dur, str):
                nums = re.findall(r"\d+", raw_dur)
                duration = int(nums[0]) if nums else 0
            else:
                duration = int(raw_dur) if raw_dur else 0

            # Build full predecessor list with link metadata
            preds_full = []
            for p in t.get("predecessors", []):
                if isinstance(p, dict):
                    preds_full.append({
                        "task_id": str(p.get("task_id", "")),
                        "type": p.get("type", "FS"),
                        "lag_days": int(p.get("lag_days", 0) or 0),
                        "strength": p.get("strength", "hard"),
                    })
                else:
                    preds_full.append({"task_id": str(p), "type": "FS", "lag_days": 0, "strength": "hard"})

            # Legacy dependencies field
            for d in t.get("dependencies", []):
                dep_id = str(d)
                if not any(pf["task_id"] == dep_id for pf in preds_full):
                    preds_full.append({"task_id": dep_id, "type": "FS", "lag_days": 0, "strength": "hard"})

            task_map[tid] = {
                "task_id": tid,
                "duration": duration,
                "preds_full": [pf for pf in preds_full if pf["task_id"]],
                "successors": [],
                "es": None,
                "ef": None,
                "ls": None,
                "lf": None,
                "slack": 0,
                "is_critical": False,
                "is_manual": (t.get("task_mode") or "Auto") == "Manual",
                "is_summary": bool(t.get("is_summary", False)),
                "summary_type": t.get("summary_type", "auto"),
                "constraint_type": t.get("constraint_type", "ASAP"),
                "constraint_date": t.get("constraint_date"),
                "deadline": t.get("deadline"),
                "parent_id": t.get("parent_id"),
                "original": t,
            }

        # Build successors and in-degree
        in_degree = {tid: 0 for tid in task_map}
        for tid, task in task_map.items():
            for pred_entry in task["preds_full"]:
                pred_id = pred_entry["task_id"]
                if pred_id in task_map:
                    task_map[pred_id]["successors"].append(tid)
                    in_degree[tid] += 1

        # 3. TOPOLOGICAL SORT (Kahn's algorithm)
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
            return {"error": "Circular dependency detected in schedule graph."}

        # 4. FORWARD PASS
        # Manual-mode tasks: freeze their existing scheduled dates as ES/EF.
        # Auto-mode tasks: compute via CPM with full link-type + lag support.
        for tid in topo_order:
            task = task_map[tid]

            if task["is_manual"]:
                # Freeze: use existing scheduled dates if present
                orig = task["original"]
                es = _parse_date(orig.get("scheduled_start")) or project_start
                ef = _parse_date(orig.get("scheduled_finish"))
                if ef is None:
                    ef = es + timedelta(days=task["duration"])
                task["es"] = es
                task["ef"] = ef
            else:
                # Compute ES from predecessors (with link types + lag)
                es = _compute_es_from_predecessors(tid, task_map, project_start)
                ef = es + timedelta(days=task["duration"])

                # Apply constraint types
                es, ef = _apply_constraint(
                    es, ef, task["duration"],
                    task["constraint_type"], task["constraint_date"]
                )
                task["es"] = es
                task["ef"] = ef

        # 5. BACKWARD PASS
        final_ef = project_start
        if topo_order:
            final_ef = max(
                (task_map[tid]["ef"] for tid in task_map if task_map[tid]["ef"] is not None),
                default=project_start,
            )

        for tid in reversed(topo_order):
            task = task_map[tid]

            if task["is_manual"]:
                # Manual tasks: LS/LF = ES/EF (no float)
                task["lf"] = task["ef"]
                task["ls"] = task["es"]
                task["slack"] = 0
                task["is_critical"] = True
                continue

            if not task["successors"]:
                task["lf"] = final_ef
            else:
                min_ls = final_ef
                for succ_id in task["successors"]:
                    if succ_id not in task_map:
                        continue
                    succ = task_map[succ_id]
                    if succ["ls"] is None:
                        continue
                    # Determine link type from successor's preds_full
                    link_type = "FS"
                    lag = 0
                    for pf in succ["preds_full"]:
                        if pf["task_id"] == tid:
                            link_type = pf.get("type", "FS").upper()
                            lag = int(pf.get("lag_days", 0) or 0)
                            break

                    if link_type == "FS":
                        candidate_lf = succ["ls"] - timedelta(days=lag)
                    elif link_type == "SS":
                        # Pred must start before succ starts: LF = LS_succ + duration - lag
                        candidate_lf = succ["ls"] - timedelta(days=lag) + timedelta(days=task["duration"])
                    elif link_type == "FF":
                        candidate_lf = succ["lf"] - timedelta(days=lag)
                    elif link_type == "SF":
                        candidate_lf = succ["lf"] - timedelta(days=lag) + timedelta(days=task["duration"])
                    else:
                        candidate_lf = succ["ls"] - timedelta(days=lag)

                    if candidate_lf < min_ls:
                        min_ls = candidate_lf

                task["lf"] = min_ls

            task["ls"] = task["lf"] - timedelta(days=task["duration"])
            task["slack"] = (task["ls"] - task["es"]).days
            task["is_critical"] = task["slack"] <= 0

        # 6. PARENT ROLLUP for summary tasks
        # Build parent→children index
        children_map: dict = {tid: [] for tid in task_map}
        for tid, task in task_map.items():
            parent_id = task.get("parent_id")
            if parent_id and str(parent_id) in task_map:
                children_map[str(parent_id)].append(tid)

        # Process summary tasks in REVERSE topo order (bottom-up)
        for tid in reversed(topo_order):
            task = task_map[tid]
            if not task["is_summary"] or task["summary_type"] != "auto":
                continue

            child_ids = children_map.get(tid, [])
            if not child_ids:
                continue

            child_tasks = [task_map[c] for c in child_ids if c in task_map]
            child_tasks = [c for c in child_tasks if c["es"] is not None]
            if not child_tasks:
                continue

            # Rollup: MIN(child ES), MAX(child EF)
            task["es"] = min(c["es"] for c in child_tasks)
            task["ef"] = max(c["ef"] for c in child_tasks)

            # Weighted percent complete by baseline_cost
            total_cost = sum(
                float(c["original"].get("baseline_cost", 0) or 0) for c in child_tasks
            )
            if total_cost > 0:
                weighted_pct = sum(
                    float(c["original"].get("percent_complete", 0) or 0)
                    * float(c["original"].get("baseline_cost", 0) or 0)
                    for c in child_tasks
                ) / total_cost
                task["original"] = dict(task["original"])
                task["original"]["percent_complete"] = round(weighted_pct, 2)

            # Duration = EF - ES in days
            task["duration"] = (task["ef"] - task["es"]).days
            # Slack inherits min child slack
            task["slack"] = min(c["slack"] for c in child_tasks)
            task["is_critical"] = task["slack"] <= 0

        # 7. FORMAT OUTPUT
        output_tasks = []
        critical_path = []
        calculation_version = str(uuid.uuid4())
        calculated_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        for tid in topo_order:
            t = task_map[tid]

            if t["is_critical"]:
                critical_path.append(tid)

            updated = dict(t["original"])

            # Compute deadline variance
            deadline_variance_days = None
            is_deadline_breached = False
            if t.get("deadline") and t["ef"] is not None:
                deadline_dt = _parse_date(t["deadline"])
                if deadline_dt:
                    deadline_variance_days = (t["ef"] - deadline_dt).days
                    is_deadline_breached = deadline_variance_days > 0

            # Step 8: DRAFT → NOT_STARTED auto-transition
            current_status = updated.get("task_status", "not_started")
            if current_status == "draft":
                current_status = "not_started"

            updated.update({
                "scheduled_start": t["es"].strftime("%Y-%m-%d") if t["es"] else None,
                "scheduled_finish": t["ef"].strftime("%Y-%m-%d") if t["ef"] else None,
                "scheduled_duration": t["duration"],
                "early_start": t["es"].strftime("%Y-%m-%d") if t["es"] else None,
                "early_finish": t["ef"].strftime("%Y-%m-%d") if t["ef"] else None,
                "late_start": t["ls"].strftime("%Y-%m-%d") if t["ls"] else None,
                "late_finish": t["lf"].strftime("%Y-%m-%d") if t["lf"] else None,
                "total_slack": t["slack"],
                "is_critical": t["is_critical"],
                "task_status": current_status,
                "deadline_variance_days": deadline_variance_days,
                "is_deadline_breached": is_deadline_breached,
                "calculated_at": calculated_at,
            })
            output_tasks.append(updated)

        return {
            "tasks": output_tasks,
            "critical_path": critical_path,
            "total_duration_days": (final_ef - project_start).days,
            "status": "success",
            "calculation_version": calculation_version,
            "calculated_at": calculated_at,
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    try:
        input_data = json.load(sys.stdin)
        result = run_calculation(input_data)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
