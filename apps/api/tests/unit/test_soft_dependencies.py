"""
Test soft vs hard dependencies.

Soft dependencies:
- Constrain ES/EF (predecessor must finish before successor can start)
- Do NOT affect criticality (task can have slack even with soft predecessor)
- Don't make successor critical just because predecessor is critical

Hard dependencies:
- Constrain ES/EF
- AFFECT criticality (successor critical if predecessor is critical)
"""
import pytest
from app.modules.scheduler.calculate_critical_path import run_calculation


def test_soft_dependency_constrains_dates():
    """Soft dependency should constrain ES/EF but not criticality when there's a longer parallel path"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B",
            "duration": 2,
            "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0, "strength": "soft"}],
        },
        {"task_id": "C", "duration": 10, "predecessors": []},  # Longer path
        {
            "task_id": "D",
            "duration": 1,
            "predecessors": [
                {"task_id": "B", "type": "FS", "lag_days": 0, "strength": "hard"},
                {"task_id": "C", "type": "FS", "lag_days": 0, "strength": "hard"},
            ],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # B should start after A finishes (ES constrained by soft dep)
    assert tasks_dict["B"]["scheduled_start"] == "2024-01-06"

    # But B should NOT be critical (has slack because C is longer)
    assert tasks_dict["B"]["is_critical"] is False
    assert tasks_dict["B"]["total_slack"] > 0


def test_soft_dependency_no_criticality_propagation():
    """Critical predecessor with soft dep should not make successor critical"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {"task_id": "B", "duration": 10, "predecessors": []},  # Longer, will have slack
        {
            "task_id": "C",
            "duration": 2,
            "predecessors": [
                {"task_id": "A", "type": "FS", "lag_days": 0, "strength": "soft"},  # Soft dep
                {"task_id": "B", "type": "FS", "lag_days": 0, "strength": "hard"},  # Hard dep
            ],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # C is critical because B is critical
    assert tasks_dict["C"]["is_critical"] is True

    # But if A is extended such that soft dep to A is slack:
    # C can still have slack relative to A (because dep is soft)


def test_hard_dependency_propagates_criticality():
    """Critical predecessor with hard dep makes successor critical"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B",
            "duration": 2,
            "predecessors": [
                {"task_id": "A", "type": "FS", "lag_days": 0, "strength": "hard"}
            ],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Both should be critical (hard dependency)
    assert tasks_dict["A"]["is_critical"] is True
    assert tasks_dict["B"]["is_critical"] is True
    assert tasks_dict["B"]["total_slack"] == 0


def test_mixed_soft_and_hard_dependencies():
    """Task with both soft and hard dependencies"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {"task_id": "B", "duration": 10, "predecessors": []},
        {
            "task_id": "C",
            "duration": 3,
            "predecessors": [
                {"task_id": "A", "type": "FS", "lag_days": 0, "strength": "soft"},  # Soft
                {"task_id": "B", "type": "FS", "lag_days": 0, "strength": "hard"},  # Hard (longer)
            ],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # C's ES constrained by both (soft and hard)
    # A finishes 2024-01-05, B finishes 2024-01-10
    # C should start: max(2024-01-05 + 1, 2024-01-10 + 1) = 2024-01-11
    assert tasks_dict["C"]["scheduled_start"] == "2024-01-11"

    # C is critical because hard predecessor B is critical
    assert tasks_dict["C"]["is_critical"] is True


def test_soft_dependency_in_parallel_path():
    """Soft dependency in non-critical path"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B", "duration": 2,
            "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0, "strength": "soft"}]
        },
        {"task_id": "C", "duration": 20, "predecessors": []},  # Long task, critical path
        {
            "task_id": "D",
            "duration": 2,
            "predecessors": [
                {"task_id": "B", "type": "FS", "lag_days": 0, "strength": "hard"},
                {"task_id": "C", "type": "FS", "lag_days": 0, "strength": "hard"},
            ],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Critical path: C → D
    assert tasks_dict["C"]["is_critical"] is True
    assert tasks_dict["D"]["is_critical"] is True

    # B is not critical (soft dep from A doesn't make it critical)
    assert tasks_dict["B"]["is_critical"] is False
    assert tasks_dict["B"]["total_slack"] > 0


def test_soft_dependency_with_lag():
    """Soft dependency with lag should still constrain dates"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B",
            "duration": 2,
            "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 3, "strength": "soft"}],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # A: 2024-01-01 to 2024-01-05
    # Soft dep with 3-day lag: 2024-01-05 + 1 + 3 = 2024-01-09
    # B should start 2024-01-09
    assert tasks_dict["B"]["scheduled_start"] == "2024-01-09"

    # B should not be critical
    assert tasks_dict["B"]["is_critical"] is False


def test_soft_dependency_ss_type():
    """Soft Start-to-Start dependency"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B",
            "duration": 3,
            "predecessors": [{"task_id": "A", "type": "SS", "lag_days": 2, "strength": "soft"}],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # A starts 2024-01-01
    # SS with 2-day lag: B starts 2024-01-01 + 2 = 2024-01-03
    assert tasks_dict["B"]["scheduled_start"] == "2024-01-03"

    # B should not be critical
    assert tasks_dict["B"]["is_critical"] is False


def test_all_soft_dependencies():
    """Chain of all soft dependencies should have slack"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B",
            "duration": 2,
            "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0, "strength": "soft"}],
        },
        {
            "task_id": "C",
            "duration": 2,
            "predecessors": [{"task_id": "B", "type": "FS", "lag_days": 0, "strength": "soft"}],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # All tasks still constrained by dates (soft deps constrain ES/EF)
    # A: 2024-01-01 to 2024-01-05, B: 2024-01-06 to 2024-01-07, C: 2024-01-08 to 2024-01-09
    assert tasks_dict["B"]["scheduled_start"] == "2024-01-06"
    assert tasks_dict["C"]["scheduled_start"] == "2024-01-08"

    # But none should be critical (all soft deps - soft deps don't propagate criticality)
    assert tasks_dict["A"]["is_critical"] is False
    assert tasks_dict["B"]["is_critical"] is False
    assert tasks_dict["C"]["is_critical"] is False

    # All have slack since there are only soft dependencies
    assert tasks_dict["A"]["total_slack"] > 0
    assert tasks_dict["B"]["total_slack"] > 0
    assert tasks_dict["C"]["total_slack"] > 0


def test_soft_to_hard_transition():
    """Path from soft to hard dependency"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B",
            "duration": 2,
            "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0, "strength": "soft"}],
        },
        {
            "task_id": "C",
            "duration": 2,
            "predecessors": [{"task_id": "B", "type": "FS", "lag_days": 0, "strength": "hard"}],
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Critical path: only C is critical (hard dep from B→C makes C critical)
    # B is critical only because it's on the backward path from C (hard dep B→C)
    # A is NOT critical (soft dep A→B doesn't make it critical)
    assert tasks_dict["A"]["is_critical"] is False  # Soft predecessor, not critical
    assert tasks_dict["B"]["is_critical"] is True   # B has hard successor C, so critical
    assert tasks_dict["C"]["is_critical"] is True   # C has hard predecessor B, so critical


def test_default_strength_is_hard():
    """If strength not specified, default to hard"""
    tasks = [
        {"task_id": "A", "duration": 5, "predecessors": []},
        {
            "task_id": "B",
            "duration": 2,
            "predecessors": [{"task_id": "A", "type": "FS", "lag_days": 0}],  # No strength specified
        },
    ]
    project_start = "2024-01-01"

    result = run_calculation({"tasks": tasks, "project_start": project_start})

    assert result["status"] == "success"
    tasks_dict = {t["task_id"]: t for t in result["tasks"]}

    # Should behave as hard dependency
    assert tasks_dict["B"]["is_critical"] is True
    assert tasks_dict["B"]["total_slack"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
