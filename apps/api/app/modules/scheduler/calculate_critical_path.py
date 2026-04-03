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


def _apply_constraint(es, ef, duration, constraint_type, constraint_date, project_start):
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
    dur_delta = timedelta(days=max(0, duration - 1))

    if ct == "ALAP":
        # As Late As Possible — handled at backward pass level; skip here
        return es, ef
    elif ct == "SNET":
        # Start No Earlier Than: ES = max(ES, constraint_date)
        if es < cd:
            es = cd
            ef = es + dur_delta
    elif ct == "SNLT":
        # Start No Later Than: ES = min(ES, constraint_date)
        if es > cd:
            # S-BUG #12: Don't allow moving before project start
            es = max(cd, project_start)
            ef = es + dur_delta
    elif ct == "FNET":
        # Finish No Earlier Than: EF = max(EF, constraint_date)
        if ef < cd:
            ef = cd
            es = ef - dur_delta
            # Also ensure ES doesn't go below project_start if possible
            if es < project_start:
                es = project_start
                ef = es + dur_delta
    elif ct == "FNLT":
        # Finish No Later Than: EF = min(EF, constraint_date)
        if ef > cd:
            ef = cd
            es = ef - dur_delta
            if es < project_start:
                es = project_start
                ef = es + dur_delta
    elif ct == "MSO":
        # Must Start On
        es = max(cd, project_start)
        ef = es + dur_delta
    elif ct == "MFO":
        # Must Finish On
        ef = max(cd, project_start + dur_delta)
        es = ef - dur_delta

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
        
        p_es = pred.get("es")
        p_ef = pred.get("ef")
        if p_es is None or p_ef is None:
            continue

        link_type = pred_entry.get("type", "FS").upper()
        lag = int(pred_entry.get("lag_days", 0) or 0)
        dur = task.get("duration", 0)
        dur_delta = timedelta(days=max(0, dur - 1))

        if link_type == "FS":
            # Successor starts after predecessor (Finish-to-Start)
            # Construction CPM: Succ_Start = Pred_Finish + 1 + Lag
            candidate = p_ef + timedelta(days=lag + 1)
        elif link_type == "SS":
            # Successor starts with predecessor (Start-to-Start)
            candidate = p_es + timedelta(days=lag)
        elif link_type == "FF":
            # Successor finishes with predecessor (Finish-to-Finish)
            # EF_succ = EF_pred + lag => ES_succ = EF_pred + lag - (dur - 1)
            candidate = p_ef + timedelta(days=lag) - dur_delta
        elif link_type == "SF":
            # Successor finishes as predecessor starts (Start-to-Finish)
            # EF_succ = ES_pred + lag => ES_succ = ES_pred + lag - (dur - 1)
            candidate = p_es + timedelta(days=lag) - dur_delta
        else:
            candidate = p_ef + timedelta(days=lag + 1)

        if candidate > max_es:
            max_es = candidate

    return max_es


def run_calculation(input_data: dict) -> dict:
    """Core calculation logic. Implements the 8-step enhanced CPM pipeline."""
    try:
        tasks_input = input_data.get("tasks", [])
        project_start_str = input_data.get("project_start")

        # Step 1: Parse Project Start
        if not project_start_str:
            project_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            project_start = _parse_date(project_start_str) or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if not tasks_input:
            return {"tasks": [], "critical_path": [], "total_duration_days": 0}

        # Step 2 & 3: Data Prep & Manual Mode Detection
        task_map = {}
        for t in tasks_input:
            tid = str(t.get("task_id", ""))
            if not tid: continue

            # Duration parsing
            raw_dur = t.get("duration") or t.get("scheduled_duration") or 0
            if isinstance(raw_dur, str):
                nums = re.findall(r"\d+", raw_dur)
                duration = int(nums[0]) if nums else 0
            else:
                duration = int(raw_dur) if raw_dur else 0

            # Dependency cleaning
            preds_processed = []
            seen_preds = set()
            raw_preds = t.get("predecessors", [])
            raw_deps = t.get("dependencies", [])
            
            for p in raw_preds:
                p_id = str(p.get("task_id", "")) if isinstance(p, dict) else str(p)
                if p_id and p_id not in seen_preds:
                    seen_preds.add(p_id)
                    preds_processed.append({
                        "task_id": p_id,
                        "type": p.get("type", "FS") if isinstance(p, dict) else "FS",
                        "lag_days": int(p.get("lag_days", 0) or 0) if isinstance(p, dict) else 0,
                        "strength": p.get("strength", "hard") if isinstance(p, dict) else "hard"
                    })
            for d in raw_deps:
                d_id = str(d)
                if d_id and d_id not in seen_preds:
                    seen_preds.add(d_id)
                    preds_processed.append({"task_id": d_id, "type": "FS", "lag_days": 0, "strength": "hard"})

            task_map[tid] = {
                "task_id": tid,
                "duration": duration,
                "preds_full": preds_processed,
                "successors": [],
                "es": None, "ef": None, "ls": None, "lf": None,
                "slack": 0, "is_critical": False,
                "is_manual": (t.get("task_mode") or "Auto") == "Manual",
                "is_summary": bool(t.get("is_summary", False)),
                "summary_type": t.get("summary_type", "auto"),
                "constraint_type": t.get("constraint_type", "ASAP"),
                "constraint_date": t.get("constraint_date"),
                "deadline": t.get("deadline"),
                "parent_id": str(t.get("parent_id", "")) if t.get("parent_id") else None,
                "original": dict(t),
            }

        # Build child index
        children_map = {tid: [] for tid in task_map}
        for tid, t in task_map.items():
            if t["parent_id"] in task_map:
                children_map[t["parent_id"]].append(tid)

        # Build successor graph and in-degree
        # To ensure summary cascade, a Summary must be calculated AFTER its children
        in_degree = {tid: 0 for tid in task_map}
        for tid, task in task_map.items():
            # Standard dependencies
            for pf in task["preds_full"]:
                if pf["task_id"] in task_map:
                    task_map[pf["task_id"]]["successors"].append(tid)
                    in_degree[tid] += 1
            # Structural dependency: child -> parent (for rollup)
            if task["parent_id"] in task_map:
                task_map[tid]["successors"].append(task["parent_id"])
                in_degree[task["parent_id"]] += 1

        # Kahn's topological sort (Optimized with deque)
        from collections import deque
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        topo_order = []
        while queue:
            curr = queue.popleft()
            topo_order.append(curr)
            for succ in task_map[curr]["successors"]:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(topo_order) < len(task_map):
            cycle_tasks = [tid for tid, deg in in_degree.items() if deg > 0]
            # Try to build a small chain for the error message
            error_msg = f"Circular dependency detected involving tasks: {', '.join(cycle_tasks[:5])}"
            if len(cycle_tasks) > 5:
                error_msg += f" and {len(cycle_tasks) - 5} others"
            return {"error": error_msg, "status": "failed", "cycle_task_ids": cycle_tasks}

        # Step 4: Forward Pass (Integrated Rollup)
        for tid in topo_order:
            task = task_map[tid]
            dur_delta = timedelta(days=max(0, task["duration"] - 1))
            
            if task["is_manual"]:
                orig = task["original"]
                task["es"] = _parse_date(orig.get("scheduled_start")) or project_start
                task["ef"] = _parse_date(orig.get("scheduled_finish")) or (task["es"] + dur_delta)
                task["calc_reason"] = "Manual date override"
            elif task["is_summary"] and task["summary_type"] == "auto":
                kids = [task_map[k] for k in children_map[tid]]
                if kids:
                    task["es"] = min(k["es"] for k in kids if k["es"] is not None)
                    task["ef"] = max(k["ef"] for k in kids if k["ef"] is not None)
                    task["duration"] = max(0, (task["ef"] - task["es"]).days + 1)
                    task["calc_reason"] = f"Rolled up from {len(kids)} child tasks"
                    
                    # Progress Rollup with Clamping
                    total_weight = sum(float(k["original"].get("baseline_cost", 1.0) or 1.0) for k in kids)
                    if total_weight > 0:
                        w_sum = sum(float(k["original"].get("percent_complete", 0) or 0) * float(k["original"].get("baseline_cost", 1.0) or 1.0) for k in kids)
                        p_val = round(w_sum / total_weight, 2)
                    else:
                        p_val = round(sum(float(k["original"].get("percent_complete", 0) or 0) for k in kids) / len(kids), 2)
                    task["original"]["percent_complete"] = max(0, min(100, p_val))
                else:
                    task["es"] = _compute_es_from_predecessors(tid, task_map, project_start)
                    task["ef"] = task["es"] + dur_delta
                    task["calc_reason"] = "Start of project (No children)"
            else:
                # Normal CPM
                task_preds = task["preds_full"]
                if not task_preds:
                    task["es"] = project_start
                    task["calc_reason"] = "Project start"
                else:
                    # Find driving predecessor
                    max_es = project_start
                    driver = "Project Start"
                    for pred_entry in task_preds:
                        pred_id = pred_entry["task_id"]
                        if pred_id not in task_map: continue
                        pred = task_map[pred_id]
                        p_ef = pred.get("ef")
                        if p_ef is None: continue
                        
                        link_type = pred_entry.get("type", "FS").upper()
                        lag = int(pred_entry.get("lag_days", 0) or 0)
                        
                        if link_type == "FS":
                            candidate = p_ef + timedelta(days=lag + 1)
                        elif link_type == "SS":
                            candidate = pred.get("es") + timedelta(days=lag)
                        else:
                            candidate = p_ef + timedelta(days=lag + 1)
                            
                        if candidate > max_es:
                            max_es = candidate
                            driver = f"Predecessor {pred_id} ({link_type}+{lag}d)"
                    
                    task["es"] = max_es
                    task["calc_reason"] = driver

                task["ef"] = task["es"] + dur_delta
                
                # Apply constraint influence
                if task["constraint_type"] != "ASAP":
                    old_es = task["es"]
                    task["es"], task["ef"] = _apply_constraint(task["es"], task["ef"], task["duration"], task["constraint_type"], task["constraint_date"], project_start)
                    if task["es"] != old_es:
                        task["calc_reason"] += f" | Adjusted by {task['constraint_type']} constraint"

        # Step 6: Backward Pass (CPM Late Dates)
        final_ef = project_start
        if topo_order:
            valid_efs = [t["ef"] for t in task_map.values() if t["ef"] is not None]
            final_ef = max(valid_efs) if valid_efs else project_start

        for tid in reversed(topo_order):
            task = task_map[tid]
            dur_delta = timedelta(days=max(0, task["duration"] - 1))
            
            if task["is_manual"]:
                task["lf"], task["ls"], task["slack"], task["is_critical"] = task["ef"], task["es"], 0, True
                continue
            
            task["lf"] = final_ef
            valid_successors = False
            for succ_id in task["successors"]:
                succ = task_map[succ_id]
                if succ["parent_id"] == tid: continue 

                valid_successors = True
                link_type = "FS"
                lag = 0
                for pf in succ["preds_full"]:
                    if pf["task_id"] == tid:
                        link_type = pf.get("type", "FS").upper()
                        lag = int(pf.get("lag_days", 0) or 0)
                        break
                
                s_ls = succ["ls"] if succ["ls"] is not None else succ["es"]
                s_lf = succ["lf"] if succ["lf"] is not None else succ["ef"]
                if s_ls is None: s_ls = final_ef
                if s_lf is None: s_lf = final_ef

                if link_type == "FS": 
                    # pred_LF <= succ_LS - 1 - lag
                    candidate = s_ls - timedelta(days=lag + 1)
                elif link_type == "SS": 
                    # pred_LS <= succ_LS - lag => pred_LF <= succ_LS - lag + (dur - 1)
                    candidate = s_ls - timedelta(days=lag) + dur_delta
                elif link_type == "FF": 
                    candidate = s_lf - timedelta(days=lag)
                elif link_type == "SF": 
                    # pred_LS <= succ_LF - lag => pred_LF <= succ_LF - lag + (dur - 1)
                    candidate = s_lf - timedelta(days=lag) + dur_delta
                else: 
                    candidate = s_ls - timedelta(days=lag + 1)
                
                if candidate < task["lf"]: task["lf"] = candidate

            task["ls"] = task["lf"] - dur_delta
            
            if task["constraint_type"] == "ALAP":
                task["es"], task["ef"] = task["ls"], task["lf"]

        # Step 7: Summary Rollup (Bottom-up for accurate dates, slack, and criticality)
        for tid in reversed(topo_order):
            task = task_map[tid]
            if task["is_summary"] and task["summary_type"] == "auto":
                kids = [task_map[k] for k in children_map[tid]]
                if kids:
                    # ES/EF Rollup (already done in forward, but re-verify if ALAP shifted things)
                    task["es"] = min(k["es"] for k in kids if k["es"] is not None)
                    task["ef"] = max(k["ef"] for k in kids if k["ef"] is not None)
                    task["duration"] = (task["ef"] - task["es"]).days + 1
                    
                    # LS/LF Rollup
                    task["ls"] = min(k["ls"] for k in kids if k["ls"] is not None)
                    task["lf"] = max(k["lf"] for k in kids if k["lf"] is not None)
                    
                    # Slack & Criticality Rollup
                    task["slack"] = min(k["slack"] for k in kids)
                    task["is_critical"] = any(k["is_critical"] for k in kids)
                else:
                    task["slack"] = (task["ls"] - task["es"]).days
                    task["is_critical"] = task["slack"] <= 0
            else:
                # Re-calculate slack for non-summaries in case ALAP/MSO shifted ES but not LS
                task["slack"] = (task["ls"] - task["es"]).days
                task["is_critical"] = task["slack"] <= 0

        # Step 8: Output assembly
        output_tasks = []
        critical_path = []
        calc_version = str(uuid.uuid4())
        calc_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        for tid in topo_order:
            t = task_map[tid]
            if t["is_critical"]: critical_path.append(tid)

            node = dict(t["original"])
            # Remove silent promotion check - preserve status as is
            # if node.get("task_status") == "draft": node["task_status"] = "not_started"

            dv, db = None, False
            if t.get("deadline") and t["ef"]:
                dl = _parse_date(t["deadline"])
                if dl:
                    dv = (t["ef"] - dl).days
                    db = dv > 0

            node.update({
                "scheduled_start": t["es"].strftime("%Y-%m-%d") if t["es"] else None,
                "scheduled_finish": t["ef"].strftime("%Y-%m-%d") if t["ef"] else None,
                "duration": t["duration"],
                "scheduled_duration": t["duration"],
                "early_start": t["es"].strftime("%Y-%m-%d") if t["es"] else None,
                "early_finish": t["ef"].strftime("%Y-%m-%d") if t["ef"] else None,
                "late_start": t["ls"].strftime("%Y-%m-%d") if t["ls"] else None,
                "late_finish": t["lf"].strftime("%Y-%m-%d") if t["lf"] else None,
                "total_slack": t["slack"],
                "is_critical": t["is_critical"],
                "deadline_variance_days": dv,
                "is_deadline_breached": db,
                "calculation_version": calc_version,
                "calculated_at": calc_at,
                "calc_reason": t.get("calc_reason"),
            })
            output_tasks.append(node)

        return {
            "tasks": output_tasks,
            "critical_path": critical_path,
            "total_duration_days": max(0, (final_ef - project_start).days + 1),
            "status": "success",
            "calculation_version": calc_version,
            "calculated_at": calc_at,
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}


if __name__ == "__main__":
    try:
        data = json.load(sys.stdin)
        print(json.dumps(run_calculation(data)))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
