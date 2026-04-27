"""
Comprehensive CPM algorithm tests covering all calculation paths.
Tests: simple chains, parallel tasks, constraints, dependencies, circular detection, rollup.
"""
from datetime import datetime
from app.modules.scheduler.calculate_critical_path import run_calculation


def test_simple_chain_a_b_c():
    """Test simple linear dependency: A→B→C"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {"task_id": "B", "duration": 3, "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0}]},
        {"task_id": "C", "duration": 2, "predecessors": [{"task_id": "B", "type": "FS", "lag_days": 0}]},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    assert len(result["tasks"]) == 3
    assert result["total_duration_days"] == 10  # 5 + 3 + 2

    # Verify critical path
    assert len(result["critical_path"]) == 3  # All tasks critical in simple chain
    assert set(result["critical_path"]) == {"A", "B", "C"}


def test_parallel_tasks():
    """Test parallel branches: A→C, A→B, merged at D"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {"task_id": "B", "duration": 3, "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0}]},
        {"task_id": "C", "duration": 7, "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0}]},
        {"task_id": "D", "duration": 2, "predecessors": [
            {"task_id": "B", "type": "FS", "lag_days": 0},
            {"task_id": "C", "type": "FS", "lag_days": 0}
        ]},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    assert result["total_duration_days"] == 14  # 5 + 7 + 2
    assert "C" in result["critical_path"]  # C is longer than B
    assert "B" not in result["critical_path"]  # B has slack


def test_finish_to_finish_dependency():
    """Test FF (Finish-to-Finish) link type"""
    tasks = [
        {"task_id": "A", "duration": 10, "predecessors": []},
        {"task_id": "B", "duration": 5, "predecessors": [{"task_id": "A", "type": "FF", "lag_days": 0}]},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # B should finish at same time as A
    assert tasks_dict["B"]["scheduled_finish"] == tasks_dict["A"]["scheduled_finish"]


def test_start_to_start_dependency():
    """Test SS (Start-to-Start) link type"""
    tasks = [
        {"task_id": "A", "duration": 10, "predecessors": []},
        {"task_id": "B", "duration": 5, "predecessors": [{"task_id": "A", "type": "SS", "lag_days": 0}]},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # B should start at same time as A
    assert tasks_dict["B"]["scheduled_start"] == tasks_dict["A"]["scheduled_start"]


def test_dependency_with_lag():
    """Test lag days on dependencies"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {"task_id": "B", "duration": 3, "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 2}]},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # A finishes on 2024-01-05, 2-day lag, B starts 2024-01-08
    # A: Jan 1-5 (5 days), lag 2 days, B: Jan 8-10
    assert tasks_dict["B"]["scheduled_start"] == "2024-01-08"


def test_asap_constraint():
    """Test ASAP constraint (default)"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": [], "constraint_type": "ASAP"},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    assert tasks_dict["A"]["scheduled_start"] == "2024-01-01"


def test_snet_constraint():
    """Test SNET (Start No Earlier Than) constraint"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": [], "constraint_type": "SNET", "constraint_date": "2024-01-10"},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Should start no earlier than constraint date
    assert tasks_dict["A"]["scheduled_start"] == "2024-01-10"


def test_snlt_constraint():
    """Test SNLT (Start No Later Than) constraint"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": [], "constraint_type": "SNLT", "constraint_date": "2024-01-05"},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Should start no later than constraint date
    assert tasks_dict["A"]["scheduled_start"] <= "2024-01-05"


def test_mso_constraint():
    """Test MSO (Must Start On) constraint"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": [], "constraint_type": "MSO", "constraint_date": "2024-01-15"},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    assert tasks_dict["A"]["scheduled_start"] == "2024-01-15"


def test_circular_dependency_detection():
    """Test circular dependency detection"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": [{"task_id": "C", "type": "FS"}]},
        {"task_id": "B", "duration": 3, "predecessors": [{"task_id": "A", "type": "FS"}]},
        {"task_id": "C", "duration": 2, "predecessors": [{"task_id": "B", "type": "FS"}]},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "failed"
    assert "error" in result
    assert "Circular" in result["error"]


def test_summary_task_rollup():
    """Test summary task date rollup from children"""
    tasks = [
        {"task_id": "Summary", "duration": 0, "predecessors": [], "is_summary": True, "summary_type": "auto"},
        {"task_id": "Child1", "duration": 5, "predecessors": [], "parent_id": "Summary"},
        {"task_id": "Child2", "duration": 3, "predecessors": [], "parent_id": "Summary"},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Summary should span from earliest child start to latest child finish
    summary = tasks_dict["Summary"]
    child1 = tasks_dict["Child1"]
    tasks_dict["Child2"]

    assert summary["scheduled_start"] == child1["scheduled_start"]  # Both start at project start
    assert summary["scheduled_finish"] == child1["scheduled_finish"]  # Longest child


def test_slack_calculation():
    """Test slack calculation for non-critical tasks"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {"task_id": "B", "duration": 3, "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0}]},
        {"task_id": "C", "duration": 10, "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0}]},
        {"task_id": "D", "duration": 2, "predecessors": [
            {"task_id": "B", "type": "FS", "lag_days": 0},
            {"task_id": "C", "type": "FS", "lag_days": 0}
        ]},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # B has slack because C is longer
    assert tasks_dict["B"]["total_slack"] > 0
    assert not tasks_dict["B"]["is_critical"]

    # C is critical (longest path)
    assert tasks_dict["C"]["total_slack"] == 0
    assert tasks_dict["C"]["is_critical"]


def test_manual_mode_dates():
    """Test manual mode (scheduled dates are fixed)"""
    tasks = [
        {
            "task_id": "A", "duration": 5, "predecessors": [],
            "task_mode": "Manual",
            "scheduled_start": "2024-02-01", "scheduled_finish": "2024-02-10"
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Manual task should keep its scheduled dates
    assert tasks_dict["A"]["scheduled_start"] == "2024-02-01"
    assert tasks_dict["A"]["scheduled_finish"] == "2024-02-10"


def test_empty_task_list():
    """Test with empty task list"""
    result = run_calculation({"tasks": [], "project_start": "2024-01-01"})

    assert result["status"] == "success"
    assert len(result["tasks"]) == 0
    assert result["total_duration_days"] == 0


def test_single_task():
    """Test with single task"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    assert len(result["tasks"]) == 1
    assert result["total_duration_days"] == 5
    assert result["critical_path"] == ["A"]


def test_duration_delta_consistency():
    """Verify duration delta is calculated consistently"""
    tasks = [
        {"task_id": "A", "duration": 10, "predecessors": []},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Duration should be consistent: (ef - es).days + 1 = duration
    task_a = tasks_dict["A"]
    start = datetime.strptime(task_a["scheduled_start"], "%Y-%m-%d")
    finish = datetime.strptime(task_a["scheduled_finish"], "%Y-%m-%d")

    calculated_duration = (finish - start).days + 1
    assert calculated_duration == 10


def test_multiple_constraints_on_same_task():
    """Test task with predecessor and constraint"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B", "duration": 3,
            "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0}],
            "constraint_type": "SNET", "constraint_date": "2024-01-10"
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # B should start at later of: predecessor finish + 1, or constraint date
    # A finishes 2024-01-05, so B would start 2024-01-06
    # But constraint says SNET 2024-01-10, so B starts 2024-01-10
    assert tasks_dict["B"]["scheduled_start"] == "2024-01-10"


def test_deadline_variance():
    """Test deadline variance calculation"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": [], "deadline": "2024-01-08"},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # A finishes 2024-01-05, deadline 2024-01-08, variance = -3 days (early)
    assert tasks_dict["A"]["deadline_variance_days"] == -3
    assert tasks_dict["A"]["is_deadline_breached"] is False


def test_deadline_breached():
    """Test deadline breach detection"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": [], "deadline": "2024-01-02"},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # A finishes 2024-01-05, deadline 2024-01-02, breached
    assert tasks_dict["A"]["deadline_variance_days"] > 0
    assert tasks_dict["A"]["is_deadline_breached"] is True


def test_backward_pass_late_dates():
    """Test backward pass calculates late dates correctly"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {"task_id": "B", "duration": 3, "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0}]},
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    task_b = tasks_dict["B"]
    # B is critical, so LS = ES and LF = EF
    assert task_b["late_start"] == task_b["scheduled_start"]
    assert task_b["late_finish"] == task_b["scheduled_finish"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
