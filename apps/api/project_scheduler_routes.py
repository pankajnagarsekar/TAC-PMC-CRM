from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from typing import List, Dict, Any, Optional
import subprocess
import json
import os
import sys
import shutil
from datetime import datetime, timezone
from bson import ObjectId, Decimal128
from auth import get_current_user
from core.database import db_manager
from decimal import Decimal

scheduler_router = APIRouter()

# Layer 2: Orchestration

def run_scheduler_script(script_name: str, input_data: dict) -> dict:
    """Orchestrate calls to standalone, deterministic Python scripts (Layer 3)"""
    script_path = os.path.join(os.path.dirname(__file__), "execution", "scheduler", script_name)
    
    try:
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=json.dumps(input_data))
        
        if process.returncode != 0:
            # Self-Annealing Loop: Log error to suggest fixes for script & directive
            error_msg = f"Scheduler execution error for {script_name}: {stderr or stdout}"
            log_error_to_directive(script_name, error_msg)
            raise Exception(error_msg)
            
        return json.loads(stdout)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def log_error_to_directive(script_name: str, error: str):
    """Implement Error-to-Directive loop by writing logs for Layer 1 review"""
    log_dir = ".tmp/execution_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{script_name}_error.log")
    
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] ERROR: {error}\n")
        f.write("PROPOSED FIX: Review date math in calculation engine. Specifically, update the Goa Work Week logic or holiday exceptions.\n")
        f.write("DIRECTIVE UPDATE: Update apps/web/memory/project_scheduler.md to include this new case (e.g., Leap Year or Public Holiday).\n")

async def verify_financial_baseline(project_id: str, scheduled_total: float):
    """Verification Step: compare calculated project total against CRM's financial baseline"""
    # Sum all grand_total of work_orders for this project
    try:
        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
        ]
        result = await db_manager.db.work_orders.aggregate(pipeline).to_list(length=1)
        
        baseline_total = 0.0
        if result:
            val = result[0].get("total", 0)
            if isinstance(val, Decimal128):
                baseline_total = float(val.to_decimal())
            else:
                baseline_total = float(val)
        
        # We allow a small margin for rounding or if scheduled items aren't yet WOs
        if scheduled_total > baseline_total:
             # This is a critical check per the SOP
             # We should return a warning or proceed with awareness
             return {"is_aligned": False, "difference": scheduled_total - baseline_total, "baseline": baseline_total}
        
        return {"is_aligned": True, "baseline": baseline_total}
    except Exception as e:
        print(f"Baseline verification error: {str(e)}")
        return {"is_aligned": False, "error": str(e)}

def perform_intelligence_review(tasks: List[Dict[str, Any]]):
    """Multi-Agent Review Pattern: Check for common failures in MSP-style modules"""
    review_results = {"warnings": [], "errors": []}
    
    # 1. Circular Dependency Check
    visited = set()
    stack = set()
    task_map = {t["id"]: t.get("predecessors", []) for t in tasks}
    
    def has_cycle(tid):
        visited.add(tid)
        stack.add(tid)
        for pid in task_map.get(tid, []):
            if pid not in visited:
                if has_cycle(pid): return True
            elif pid in stack:
                return True
        stack.remove(tid)
        return False
        
    for tid in task_map:
        if tid not in visited:
            if has_cycle(tid):
                review_results["errors"].append(f"Circular dependency detected involving task {tid}")
                break
                
    # 2. Floating Tasks Check
    floating_tasks = [t["id"] for t in tasks if not t.get("predecessors")]
    if len(tasks) > 5 and len(floating_tasks) / len(tasks) > 0.3:
        review_results["warnings"].append(f"High number of floating tasks ({len(floating_tasks)}). Ensure proper baseline links.")
        
    return review_results

@scheduler_router.post("/{project_id}/calculate", response_model=Dict[str, Any])
async def calculate_schedule(project_id: str, data: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    """Orchestrates schedule calculation with intelligence review and financial verification"""
    tasks = data.get("tasks", [])
    project_start = data.get("project_start", "01-01-26")
    
    # 1. Intelligence Review (Layer 2)
    review = perform_intelligence_review(tasks)
    if review["errors"]:
        raise HTTPException(status_code=400, detail={"review_errors": review["errors"]})
    
    # 2. Run Layer 3 Script
    input_payload = {"tasks": tasks, "project_start": project_start}
    results = run_scheduler_script("calculate_critical_path.py", input_payload)
    
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
        
    # 3. Verification Step
    total_cost = sum(float(t.get("cost", 0)) for t in tasks)
    verification = await verify_financial_baseline(project_id, total_cost)
    
    return {
        "project_id": project_id,
        "tasks": results,
        "review": review,
        "verification": verification,
        "total_scheduled_cost": total_cost,
        "status": "Calculated"
    }

@scheduler_router.post("/{project_id}/report/cash-flow", response_model=Dict[str, Any])
async def generate_cash_flow_forecast(project_id: str, current_user: dict = Depends(get_current_user)):
    """Orchestrates cash flow report generation from saved schedule"""
    organisation_id = current_user.get("organisation_id")
    schedule = await db_manager.db.project_schedules.find_one({
        "project_id": project_id,
        "organisation_id": organisation_id
    })
    
    if not schedule:
        raise HTTPException(status_code=404, detail="No schedule found for this project. Calculate first.")
    
    # Pre-calculated tasks were saved in Mongo
    tasks = schedule.get("tasks", [])
    report_result = run_scheduler_script("generate_cash_report.py", {"tasks": tasks})
    
    return report_result

@scheduler_router.post("/{project_id}/export/pdf")
async def trigger_pdf_export(project_id: str, current_user: dict = Depends(get_current_user)):
    """Triggers the high-fidelity PDF export using ReportLab (MS Project-style Gantt)"""
    organisation_id = current_user.get("organisation_id")

    # Continuity Registry: Track state
    from execution.scheduler.continuity_manager import update_milestone
    update_milestone(project_id, "ExportTriggered")

    try:
        # Load the saved schedule from MongoDB
        schedule = await db_manager.db.project_schedules.find_one({
            "project_id": project_id,
            "organisation_id": organisation_id
        })

        if not schedule:
            raise HTTPException(status_code=404, detail="No schedule found. Please calculate and save the schedule first.")

        tasks = schedule.get("tasks", [])
        project_name = schedule.get("project_name", f"Project {project_id}")

        if not tasks:
            raise HTTPException(status_code=400, detail="Schedule has no tasks. Please add tasks before exporting.")

        # Prepare input for PDF generator
        update_milestone(project_id, "RenderingStart")

        output_path = f".tmp/gantt_export_{project_id}.pdf"
        input_payload = {
            "project_id": project_id,
            "project_name": project_name,
            "tasks": tasks,
            "output_path": output_path
        }

        # Run the PDF export script (Layer 3)
        export_result = run_scheduler_script("render_gantt_pdf.py", input_payload)

        if "error" in export_result:
            update_milestone(project_id, "ExportComplete", status="Failed")
            raise HTTPException(status_code=500, detail=export_result["error"])

        update_milestone(project_id, "ExportComplete", status="Success")
        return {
            **export_result,
            "download_url": f"/api/projects/{project_id}/export/download"
        }

    except HTTPException:
        raise
    except Exception as e:
        update_milestone(project_id, "ExportComplete", status="Failed")
        raise HTTPException(status_code=500, detail=str(e))

@scheduler_router.post("/{project_id}/import")
async def import_schedule(project_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Imports project schedule from XML (MSPDI), MPP, or PDF file"""
    # 1. Save temp file
    temp_dir = ".tmp/imports"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"import_{project_id}_{file.filename}")

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Detect file type and route to appropriate parser
        file_ext = os.path.splitext(file.filename)[1].lower()
        print(f"DEBUG: Import file: {file.filename}, detected extension: {file_ext}")

        if file_ext == ".pdf":
            script_name = "pdf_schedule_parser.py"
        elif file_ext == ".xml":
            script_name = "mpp_parser.py"  # mpp_parser handles both XML and MPP
        elif file_ext == ".mpp":
            script_name = "mpp_parser.py"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Please use .xml (MSPDI format), .mpp, or .pdf"
            )

        # 3. Run Import Script (Layer 3)
        input_payload = {"file_path": temp_path}
        results = run_scheduler_script(script_name, input_payload)

        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

@scheduler_router.post("/{project_id}/save")
async def save_schedule(project_id: str, data: Dict[str, Any], current_user: dict = Depends(get_current_user)):
    """Save the current schedule state to MongoDB"""
    user_id = current_user.get("user_id")
    organisation_id = current_user.get("organisation_id")
    
    schedule_doc = {
        "project_id": project_id,
        "organisation_id": organisation_id,
        "tasks": data.get("tasks", []),
        "project_start": data.get("project_start"),
        "total_cost": data.get("total_cost"),
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db_manager.db.project_schedules.update_one(
        {"project_id": project_id},
        {"$set": schedule_doc},
        upsert=True
    )
    
    return {"message": "Project schedule saved successfully"}

@scheduler_router.get("/{project_id}/load")
async def load_schedule(project_id: str, current_user: dict = Depends(get_current_user)):
    """Load the project schedule state"""
    organisation_id = current_user.get("organisation_id")
    schedule = await db_manager.db.project_schedules.find_one({
        "project_id": project_id,
        "organisation_id": organisation_id
    })
    
    if not schedule:
        return {"project_id": project_id, "tasks": [], "project_start": None, "total_cost": 0}
        
    # Handle bson types
    schedule["_id"] = str(schedule["_id"])
    if "updated_at" in schedule:
        schedule["updated_at"] = schedule["updated_at"].isoformat()
        
    return schedule

@scheduler_router.get("/{project_id}/export/status")
async def check_export_status(project_id: str, current_user: dict = Depends(get_current_user)):
    """Agent Memory & Continuity: tracks the state of long-running schedule exports"""
    registry_path = ".tmp/continuity_registry.json"
    
    if not os.path.exists(registry_path):
        return {"status": "Not Started"}
        
    with open(registry_path, "r") as f:
        registry = json.load(f)
        
    project_export = registry.get(project_id, {"status": "Idle"})
    return project_export
