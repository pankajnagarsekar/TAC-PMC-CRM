import sys
import json
import uuid
from datetime import datetime, timedelta


try:
    from app.modules.scheduler.resource_calendar import ResourceCalendar
except ImportError:
    # Fallback for standalone script execution
    import os
    sys.path.append(os.path.dirname(__file__))
    try:
        from resource_calendar import ResourceCalendar
    except ImportError:
        ResourceCalendar = None


def _parse_date(date_str):
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str

    # Try common formats
    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ"
    ):
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except Exception:
            continue
    try:
        # Try fromisoformat with Z handling
        s = str(date_str).strip().replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _apply_constraint(es, ef, duration, constraint_type, constraint_date, project_start, calendar=None):
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

    def add_dur(start, dur):
        if not calendar or dur <= 0:
            return start + timedelta(days=max(0, dur - 1))
        return calendar.add_working_days(start, dur - 1)

    def sub_dur(finish, dur):
        if not calendar or dur <= 0:
            return finish - timedelta(days=max(0, dur - 1))
        return calendar.next_working_day(finish, -(dur - 1))

    if ct == "ALAP":
        # As Late As Possible — handled at backward pass level; skip here
        return es, ef
    elif ct == "SNET":
        # Start No Earlier Than: ES = max(ES, constraint_date)
        if es < cd:
            es = cd
            ef = add_dur(es, duration)
    elif ct == "SNLT":
        # Start No Later Than: ES = min(ES, constraint_date)
        if es > cd:
            es = max(cd, project_start)
            ef = add_dur(es, duration)
    elif ct == "FNET":
        # Finish No Earlier Than: EF = max(EF, constraint_date)
        if ef < cd:
            ef = cd
            es = sub_dur(ef, duration)
            if es < project_start:
                es = project_start
                ef = add_dur(es, duration)
    elif ct == "FNLT":
        # Finish No Later Than: EF = min(EF, constraint_date)
        if ef > cd:
            ef = cd
            es = sub_dur(ef, duration)
            if es < project_start:
                es = project_start
                ef = add_dur(es, duration)
    elif ct == "MSO":
        # Must Start On
        es = max(cd, project_start)
        ef = add_dur(es, duration)
    elif ct == "MFO":
        # Must Finish On
        ef = max(cd, add_dur(project_start, duration))
        es = sub_dur(ef, duration)

    return es, ef


def _get_calendar(input_data: dict) -> ResourceCalendar:
    """Initialize ResourceCalendar from input payload."""
    cal_data = input_data.get("calendar")
    if not cal_data or not ResourceCalendar:
        return None

    return ResourceCalendar.from_dict(cal_data)


def _compute_es_from_predecessors(task_id, task_map, project_start, calendar=None):
    """
    Compute ES for a task based on its predecessors using FS/SS/FF/SF + lag.
    Returns (min_allowed_es, driver_description).
    """
    task = task_map[task_id]
    if not task["preds_full"]:
        return project_start, "Project Start"

    max_es = project_start
    driver = "Project Start"
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

        if link_type == "FS":
            # Finish-to-Start
            if calendar:
                candidate = calendar.add_working_days(p_ef, lag + 1)
            else:
                candidate = p_ef + timedelta(days=lag + 1)
        elif link_type == "SS":
            # Start-to-Start
            if calendar:
                candidate = calendar.add_working_days(p_es, lag)
            else:
                candidate = p_es + timedelta(days=lag)
        elif link_type == "FF":
            # Finish-to-Finish
            if calendar:
                target_ef = calendar.add_working_days(p_ef, lag)
                candidate = target_ef
                if dur > 1:
                    candidate = calendar.next_working_day(target_ef, -(dur - 1))
            else:
                candidate = p_ef + timedelta(days=lag) - timedelta(days=max(0, dur - 1))
        elif link_type == "SF":
            # Start-to-Finish
            if calendar:
                target_ef = calendar.add_working_days(p_es, lag)
                candidate = target_ef
                if dur > 1:
                    candidate = calendar.next_working_day(target_ef, -(dur - 1))
            else:
                candidate = p_es + timedelta(days=lag) - timedelta(days=max(0, dur - 1))
        else:
            if calendar:
                candidate = calendar.add_working_days(p_ef, lag + 1)
            else:
                candidate = p_ef + timedelta(days=lag + 1)

        if candidate > max_es:
            max_es = candidate
            driver = f"Predecessor {pred_id} ({link_type}+{lag}d)"

    return max_es, driver


def run_calculation(input_data: dict) -> dict:
    """
    The main CPM engine entry point.
    Expects input_data with 'tasks' (list) and 'project_start' (ISO string).
    """
    try:
        tasks = input_data.get("tasks", [])
        project_start_str = input_data.get("project_start")
        project_start = _parse_date(project_start_str) or datetime.utcnow()
        calendar = _get_calendar(input_data)

        if not tasks:
            return {
                "tasks": [],
                "critical_path": [],
                "total_duration_days": 0,
                "status": "success",
                "calculation_version": str(uuid.uuid4()),
                "calculated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        # Step 1: Pre-process and map tasks
        task_map = {}
        children_map = {}  # parent_id -> list of child_ids
        for t in tasks:
            tid = str(t["task_id"])
            task_map[tid] = {
                "task_id": tid,
                "duration": int(t.get("duration", 0)),
                "predecessors": t.get("predecessors", []),
                "parent_id": t.get("parent_id"),
                "is_summary": t.get("is_summary", False),
                "summary_type": t.get("summary_type", "auto"),
                "is_manual": t.get("task_mode") == "Manual",
                "constraint_type": t.get("constraint_type", "ASAP").upper(),
                "constraint_date": t.get("constraint_date"),
                "deadline": t.get("deadline"),
                "original": t,
                "es": None, "ef": None, "ls": None, "lf": None,
                "slack": 0, "is_critical": False,
                "successors": [],  # To be filled
                "preds_full": t.get("predecessors", []),  # Standardized list
            }
            pid = t.get("parent_id")
            if pid:
                if pid not in children_map:
                    children_map[pid] = []
                children_map[pid].append(tid)

        # Step 2: Build graph and calculate in-degrees
        in_degree = {tid: 0 for tid in task_map}
        is_hard_path = set()  # Tasks on hard dependency path

        for tid, task in task_map.items():
            for pred_entry in task["preds_full"]:
                pred_id = str(pred_entry["task_id"])
                strength = pred_entry.get("strength", "hard")

                if pred_id in task_map:
                    task_map[pred_id]["successors"].append({
                        "task_id": tid,
                        "type": pred_entry.get("type", "FS"),
                        "strength": strength,
                        "lag_days": pred_entry.get("lag_days", 0)
                    })
                    in_degree[tid] += 1
                    if strength == "hard":
                        is_hard_path.add(tid)
                        is_hard_path.add(pred_id)

        # Refine is_hard_path: Completely standalone tasks are also part of the hard sequence
        for tid, task in task_map.items():
            if not task["preds_full"] and not task["successors"]:
                is_hard_path.add(tid)

        # Kahn's topological sort (Optimized with deque)
        from collections import deque
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        topo_order = []
        while queue:
            curr = queue.popleft()
            topo_order.append(curr)
            for succ_entry in task_map[curr]["successors"]:
                succ = succ_entry["task_id"]
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(topo_order) < len(task_map):
            cycle_tasks = [tid for tid, deg in in_degree.items() if deg > 0]
            error_msg = f"Circular dependency detected involving tasks: {', '.join(cycle_tasks[:5])}"
            if len(cycle_tasks) > 5:
                error_msg += f" and {len(cycle_tasks) - 5} others"
            return {"error": error_msg, "status": "failed", "cycle_task_ids": cycle_tasks}

        # Step 4: Forward Pass (Integrated Rollup)
        for tid in topo_order:
            task = task_map[tid]

            def add_dur(start, dur):
                if not calendar or dur <= 0:
                    return start + timedelta(days=max(0, dur - 1))
                return calendar.add_working_days(start, dur - 1)

            if task["is_manual"]:
                orig = task["original"]
                # Try multiple sources for manual dates to prevent "flattening" (HIGH-07)
                manual_es = (
                    _parse_date(orig.get("scheduled_start")) or
                    _parse_date(orig.get("early_start")) or
                    _parse_date(orig.get("baseline_start"))
                )
                task["es"] = manual_es or project_start

                manual_ef = (
                    _parse_date(orig.get("scheduled_finish")) or
                    _parse_date(orig.get("early_finish")) or
                    _parse_date(orig.get("baseline_finish"))
                )
                task["ef"] = manual_ef or add_dur(task["es"], task["duration"])
                task["calc_reason"] = "Manual date override"
            else:
                # Normal CPM
                task["es"], task["calc_reason"] = _compute_es_from_predecessors(
                    tid, task_map, project_start, calendar
                )
                task["ef"] = add_dur(task["es"], task["duration"])

                # Apply constraint influence
                if task["constraint_type"] != "ASAP":
                    old_es = task["es"]
                    task["es"], task["ef"] = _apply_constraint(
                        task["es"], task["ef"], task["duration"],
                        task["constraint_type"], task["constraint_date"], project_start,
                        calendar
                    )
                    if task["es"] != old_es:
                        task["calc_reason"] += f" | Adjusted by {task['constraint_type']} constraint"

        # Step 6: Backward Pass (CPM Late Dates)
        final_ef = project_start
        for tid in topo_order:
            if task_map[tid]["ef"]:
                final_ef = max(final_ef, task_map[tid]["ef"])

        # Init LF with final EF
        for tid in topo_order:
            # If not part of a hard path, add a 1-day buffer to ensure it has slack by default
            base_lf = final_ef
            if tid not in is_hard_path:
                base_lf += timedelta(days=1)

            task_map[tid]["lf"] = base_lf
            if calendar:
                task_map[tid]["ls"] = calendar.next_working_day(base_lf, -(task_map[tid]["duration"] - 1))
            else:
                task_map[tid]["ls"] = base_lf - timedelta(days=max(0, task_map[tid]["duration"] - 1))

        # Process backward
        for tid in reversed(topo_order):
            task = task_map[tid]

            for succ_entry in task["successors"]:
                if succ_entry.get("strength") == "soft":
                    continue
                s_id = succ_entry["task_id"]
                s_ls = task_map[s_id]["ls"]
                s_lf = task_map[s_id]["lf"]
                link_type = succ_entry.get("type", "FS").upper()
                lag = int(succ_entry.get("lag_days", 0) or 0)

                if link_type == "FS":
                    if calendar:
                        candidate = calendar.next_working_day(s_ls, -(lag + 1))
                    else:
                        candidate = s_ls - timedelta(days=lag + 1)
                elif link_type == "SS":
                    if calendar:
                        ls_cand = calendar.next_working_day(s_ls, -lag)
                        candidate = add_dur(ls_cand, task["duration"])
                    else:
                        candidate = s_ls - timedelta(days=lag) + timedelta(days=max(0, task["duration"] - 1))
                elif link_type == "FF":
                    if calendar:
                        candidate = calendar.next_working_day(s_lf, -lag)
                    else:
                        candidate = s_lf - timedelta(days=lag)
                elif link_type == "SF":
                    if calendar:
                        ls_cand = calendar.next_working_day(s_lf, -lag)
                        candidate = add_dur(ls_cand, task["duration"])
                    else:
                        candidate = s_lf - timedelta(days=lag) + timedelta(days=max(0, task["duration"] - 1))
                else:
                    if calendar:
                        candidate = calendar.next_working_day(s_ls, -(lag + 1))
                    else:
                        candidate = s_ls - timedelta(days=lag + 1)

                if candidate < task["lf"]:
                    task["lf"] = candidate

            if calendar:
                task["ls"] = calendar.next_working_day(task["lf"], -(task["duration"] - 1))
            else:
                task["ls"] = task["lf"] - timedelta(days=max(0, task["duration"] - 1))

            # Slack & Criticality
            if calendar:
                task["slack"] = calendar.working_days_between(task["es"], task["ls"]) - 1
                if task["ls"] < task["es"]:
                    task["slack"] = -calendar.working_days_between(task["ls"], task["es"]) + 1
            else:
                task["slack"] = (task["ls"] - task["es"]).days

            task["is_critical"] = (task["slack"] <= 0) and (tid in is_hard_path or not task["preds_full"])

        # Step 7: Summary Rollup
        for tid in reversed(topo_order):
            task = task_map[tid]
            if task["is_summary"] and task["summary_type"] == "auto":
                kids = [task_map[k] for k in children_map.get(tid, [])]
                if kids:
                    task["es"] = min(k["es"] for k in kids if k["es"] is not None)
                    task["ef"] = max(k["ef"] for k in kids if k["ef"] is not None)
                    task["ls"] = min(k["ls"] for k in kids if k["ls"] is not None)
                    task["lf"] = max(k["lf"] for k in kids if k["lf"] is not None)
                    task["slack"] = min(k["slack"] for k in kids)
                    task["is_critical"] = any(k["is_critical"] for k in kids)

        # Step 8: Assembly
        output_tasks = []
        critical_path = [tid for tid in topo_order if task_map[tid]["is_critical"]]
        calc_version = str(uuid.uuid4())
        calc_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        for tid in topo_order:
            t = task_map[tid]
            node = dict(t["original"])

            # Calculate deadline variance
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
                "total_slack": t["slack"],
                "is_critical": t["is_critical"],
                "early_start": t["es"].strftime("%Y-%m-%d") if t["es"] else None,
                "early_finish": t["ef"].strftime("%Y-%m-%d") if t["ef"] else None,
                "late_start": t["ls"].strftime("%Y-%m-%d") if t["ls"] else None,
                "late_finish": t["lf"].strftime("%Y-%m-%d") if t["lf"] else None,
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
