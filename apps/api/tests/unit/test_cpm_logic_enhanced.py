import sys
import os
from datetime import datetime, timedelta

# Add the app directory to sys.path to import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.modules.scheduler.calculate_critical_path import run_calculation

def test_cpm_all_features():
    project_start = "2026-04-01"
    
    tasks = [
        # 1. Manual task: should stay on 2026-05-01
        {
            "task_id": "T1",
            "task_name": "Manual Task",
            "task_mode": "Manual",
            "duration": 5,
            "scheduled_start": "2026-05-01",
            "scheduled_finish": "2026-05-06"
        },
        # 2. Auto task with SS link + lag
        {
            "task_id": "T2",
            "task_name": "SS Link Task",
            "task_mode": "Auto",
            "duration": 3,
            "predecessors": [{"task_id": "T1", "type": "SS", "lag_days": 2}]
        },
        # 3. ALAP task: should be pushed to end of project
        {
            "task_id": "T3",
            "task_name": "ALAP Task",
            "task_mode": "Auto",
            "duration": 2,
            "constraint_type": "ALAP"
        },
        # 4. Must Start On task
        {
            "task_id": "T11",
            "task_name": "MSO Task",
            "task_mode": "Auto",
            "duration": 4,
            "constraint_type": "MSO",
            "constraint_date": "2026-04-10"
        },
        # 5. Summary rollup & Successor cascade
        {
            "task_id": "P1",
            "task_name": "Parent",
            "is_summary": True,
            "summary_type": "auto",
        },
        {
            "task_id": "C1",
            "task_name": "Child 1",
            "parent_id": "P1",
            "duration": 2,
            "baseline_cost": 1000,
            "percent_complete": 50,
            "predecessors": ["T11"]
        },
        {
            "task_id": "C2",
            "task_name": "Child 2",
            "parent_id": "P1",
            "duration": 4,
            "baseline_cost": 3000,
            "percent_complete": 10,
            "predecessors": ["C1"]
        },
        # Task T_SUCC depends on Parent P1
        {
            "task_id": "T_SUCC",
            "task_name": "Successor of Parent",
            "task_mode": "Auto",
            "duration": 1,
            "predecessors": ["P1"]
        },
        # 6. Draft status
        {
            "task_id": "D1",
            "task_name": "Draft Task",
            "task_status": "draft",
            "duration": 1
        }
    ]

    input_data = {
        "project_start": project_start,
        "tasks": tasks
    }

    result = run_calculation(input_data)
    
    if "error" in result:
        print(f"FAILED: {result['error']}")
        print(f"TRACE: {result.get('trace')}")
        return

    task_results = {t["task_id"]: t for t in result["tasks"]}
    
    # Assert T1 (Manual)
    assert task_results["T1"]["scheduled_start"] == "2026-05-01"
    assert task_results["T1"]["scheduled_finish"] == "2026-05-06"
    print("PASS: Manual Task dates frozen.")

    # Assert T2 (SS + 2 days lag from T1)
    assert task_results["T2"]["scheduled_start"] == "2026-05-03"
    print("PASS: SS Link + Lag working.")

    # Assert T11 (MSO 2026-04-10)
    assert task_results["T11"]["scheduled_start"] == "2026-04-10"
    print("PASS: MSO Constraint working.")

    # Assert P1 (Summary Rollup)
    # C1 starts after T11 finishes (2026-04-14)
    # C2 starts after C1 finishes (2026-04-16)
    # P1 ES = 2026-04-14, EF = 2026-04-19 (inclusive: 14,15,16,17,18,19 = 6 days)
    assert task_results["P1"]["scheduled_start"] == "2026-04-14"
    assert task_results["P1"]["scheduled_finish"] == "2026-04-19"
    print("PASS: Parent Summary dates working.")

    # Assert T_SUCC (depends on P1)
    # P1 finishes at 2026-04-19. T_SUCC should start at 2026-04-20
    assert task_results["T_SUCC"]["scheduled_start"] == "2026-04-20"
    print("PASS: Summary-to-Successor Date Cascade working.")
    
    # Progress Rollup: (50*1000 + 10*3000) / 4000 = 20
    assert task_results["P1"]["percent_complete"] == 20.0
    print("PASS: Cost-weighted progress working.")

    # Assert D1 (Draft status)
    # Status should be preserved as 'draft'
    assert task_results["D1"]["task_status"] == "draft"
    print("PASS: Draft status preservation working.")

    # Assert ALAP (T3)
    # Project finishes at 2026-05-06. T3 dur 2. LS 2026-05-05 (inclusive: 05, 06)
    assert task_results["T3"]["scheduled_start"] == "2026-05-05"
    print("PASS: ALAP Constraint working.")

    # Assert Metadata
    assert "calculation_version" in result
    assert "calculated_at" in result
    print("PASS: Metadata generated.")

    print("\nALL ENHANCED CPM TESTS PASSED!")

if __name__ == "__main__":
    test_cpm_all_features()
