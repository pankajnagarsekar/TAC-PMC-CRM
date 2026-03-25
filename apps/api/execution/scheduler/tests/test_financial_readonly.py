"""
Financial Read-Only Pipeline Tests.
Verifies that ALL financial aggregation pipelines contain ZERO write operations.

Constitution §1 Absolute Rule:
    "The PPM Scheduler has ZERO write access to legacy work_orders
     and payment_certificates collections."

Schema §2 requirement:
    "Build the read-only MongoDB aggregation pipelines in FastAPI for the
     financial handshake. All must be $lookup only — zero writes to legacy
     collections."

These tests are the automated enforcement of that rule.
They run at CI and must pass before any PR touching pipeline code is merged.
"""

import pytest
from decimal import Decimal
from execution.scheduler.pipelines.financial_aggregations import (
    build_wo_value_pipeline,
    build_payment_value_pipeline,
    build_parent_rollup_pipeline,
    assert_pipeline_is_readonly,
    compute_cost_variance_flag,
    compute_weightage_percent,
    WO_APPROVED_STATUSES,
    PC_APPROVED_STATUSES,
    _WRITE_STAGES,
    _ALLOWED_STAGES,
)

PROJECT_ID = "507f1f77bcf86cd799439011"
TASK_REFS = ["EXT-001", "EXT-002", "EXT-003"]


# =============================================================================
# Pipeline structure tests — zero write operations
# =============================================================================

class TestWOPipelineIsReadOnly:
    """Verify wo_value pipeline contains no write stages."""

    def test_no_write_stages_basic(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        assert_pipeline_is_readonly(pipeline, "wo_value")

    def test_no_write_stages_with_task_filter(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID, TASK_REFS)
        assert_pipeline_is_readonly(pipeline, "wo_value_filtered")

    def test_no_out_stage(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        stage_keys = [list(s.keys())[0] for s in pipeline]
        assert "$out" not in stage_keys

    def test_no_merge_stage(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        stage_keys = [list(s.keys())[0] for s in pipeline]
        assert "$merge" not in stage_keys

    def test_no_insert_or_update_in_lookup_subpipeline(self):
        """The $lookup subpipeline must also be read-only."""
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        for stage in pipeline:
            if "$lookup" in stage:
                subpipeline = stage["$lookup"].get("pipeline", [])
                assert_pipeline_is_readonly(subpipeline, "wo_value_lookup_subpipeline")


class TestPaymentPipelineIsReadOnly:
    """Verify payment_value pipeline contains no write stages."""

    def test_no_write_stages_basic(self):
        pipeline = build_payment_value_pipeline(PROJECT_ID)
        assert_pipeline_is_readonly(pipeline, "payment_value")

    def test_no_write_stages_with_task_filter(self):
        pipeline = build_payment_value_pipeline(PROJECT_ID, TASK_REFS)
        assert_pipeline_is_readonly(pipeline, "payment_value_filtered")

    def test_no_out_stage(self):
        pipeline = build_payment_value_pipeline(PROJECT_ID)
        stage_keys = [list(s.keys())[0] for s in pipeline]
        assert "$out" not in stage_keys

    def test_no_merge_stage(self):
        pipeline = build_payment_value_pipeline(PROJECT_ID)
        stage_keys = [list(s.keys())[0] for s in pipeline]
        assert "$merge" not in stage_keys

    def test_no_insert_or_update_in_lookup_subpipeline(self):
        pipeline = build_payment_value_pipeline(PROJECT_ID)
        for stage in pipeline:
            if "$lookup" in stage:
                subpipeline = stage["$lookup"].get("pipeline", [])
                assert_pipeline_is_readonly(subpipeline, "payment_value_lookup_subpipeline")


class TestParentRollupPipelineIsReadOnly:
    """Verify parent rollup pipeline contains no write stages."""

    def test_no_write_stages(self):
        pipeline = build_parent_rollup_pipeline(PROJECT_ID)
        assert_pipeline_is_readonly(pipeline, "parent_rollup")

    def test_no_out_stage(self):
        pipeline = build_parent_rollup_pipeline(PROJECT_ID)
        stage_keys = [list(s.keys())[0] for s in pipeline]
        assert "$out" not in stage_keys

    def test_lookup_subpipelines_readonly(self):
        pipeline = build_parent_rollup_pipeline(PROJECT_ID)
        for stage in pipeline:
            if "$lookup" in stage:
                subpipeline = stage["$lookup"].get("pipeline", [])
                assert_pipeline_is_readonly(subpipeline, "rollup_lookup_subpipeline")


class TestWriteStageDetector:
    """Verify the safety guard itself works correctly."""

    def test_detects_out_stage(self):
        bad_pipeline = [{"$match": {"x": 1}}, {"$out": "some_collection"}]
        with pytest.raises(AssertionError, match="WRITE STAGE DETECTED"):
            assert_pipeline_is_readonly(bad_pipeline, "bad_pipeline")

    def test_detects_merge_stage(self):
        bad_pipeline = [{"$match": {"x": 1}}, {"$merge": {"into": "some_collection"}}]
        with pytest.raises(AssertionError, match="WRITE STAGE DETECTED"):
            assert_pipeline_is_readonly(bad_pipeline, "bad_pipeline")

    def test_clean_pipeline_passes(self):
        good_pipeline = [
            {"$match": {"project_id": PROJECT_ID}},
            {"$lookup": {"from": "work_orders", "localField": "x", "foreignField": "y", "as": "z"}},
            {"$addFields": {"total": {"$sum": "$z.grand_total"}}},
            {"$project": {"z": 0}},
        ]
        assert_pipeline_is_readonly(good_pipeline, "good_pipeline")  # should not raise


# =============================================================================
# Pipeline structure correctness tests
# =============================================================================

class TestWOPipelineStructure:
    """Verify wo_value pipeline has the correct stage sequence."""

    def test_has_match_stage(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        stage_keys = [list(s.keys())[0] for s in pipeline]
        assert "$match" in stage_keys

    def test_has_lookup_stage(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        stage_keys = [list(s.keys())[0] for s in pipeline]
        assert "$lookup" in stage_keys

    def test_lookup_targets_work_orders(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        lookups = [s["$lookup"] for s in pipeline if "$lookup" in s]
        assert any(lk["from"] == "work_orders" for lk in lookups)

    def test_output_includes_wo_value_field(self):
        """The $addFields stage must declare wo_value."""
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        add_fields_stages = [s["$addFields"] for s in pipeline if "$addFields" in s]
        all_computed_fields = set()
        for af in add_fields_stages:
            all_computed_fields.update(af.keys())
        assert "wo_value" in all_computed_fields

    def test_output_includes_wo_retention_value_field(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        add_fields_stages = [s["$addFields"] for s in pipeline if "$addFields" in s]
        all_computed_fields = set()
        for af in add_fields_stages:
            all_computed_fields.update(af.keys())
        assert "wo_retention_value" in all_computed_fields

    def test_joined_array_is_dropped_from_output(self):
        """_matched_wos must be projected out — not exposed to clients."""
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        project_stages = [s["$project"] for s in pipeline if "$project" in s]
        # Find the cleanup projection stage
        cleanup_stages = [p for p in project_stages if "_matched_wos" in p]
        assert len(cleanup_stages) >= 1
        assert cleanup_stages[-1]["_matched_wos"] == 0

    def test_match_scopes_to_correct_project(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        match_stage = next(s["$match"] for s in pipeline if "$match" in s)
        assert match_stage["project_id"] == PROJECT_ID

    def test_match_filters_active_tasks_only(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        match_stage = next(s["$match"] for s in pipeline if "$match" in s)
        assert match_stage.get("is_active") is True

    def test_task_filter_applied_when_provided(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID, TASK_REFS)
        match_stage = next(s["$match"] for s in pipeline if "$match" in s)
        assert match_stage["external_ref_id"] == {"$in": TASK_REFS}

    def test_no_task_filter_when_not_provided(self):
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        match_stage = next(s["$match"] for s in pipeline if "$match" in s)
        assert "external_ref_id" not in match_stage

    def test_wo_lookup_filters_approved_statuses_only(self):
        """Only approved WOs must contribute to wo_value — check the subpipeline."""
        pipeline = build_wo_value_pipeline(PROJECT_ID)
        lookups = [s["$lookup"] for s in pipeline if "$lookup" in s]
        wo_lookup = next(lk for lk in lookups if lk["from"] == "work_orders")
        sub_match = next(
            s["$match"] for s in wo_lookup["pipeline"] if "$match" in s
        )
        # The status filter must reference WO_APPROVED_STATUSES
        expr = sub_match["$expr"]["$and"]
        status_filter = next(
            cond for cond in expr if "$in" in cond
        )
        assert status_filter["$in"][1] == WO_APPROVED_STATUSES


class TestPaymentPipelineStructure:
    """Verify payment_value pipeline has the correct stage sequence."""

    def test_lookup_targets_payment_certificates(self):
        pipeline = build_payment_value_pipeline(PROJECT_ID)
        lookups = [s["$lookup"] for s in pipeline if "$lookup" in s]
        assert any(lk["from"] == "payment_certificates" for lk in lookups)

    def test_output_includes_payment_value_field(self):
        pipeline = build_payment_value_pipeline(PROJECT_ID)
        add_fields_stages = [s["$addFields"] for s in pipeline if "$addFields" in s]
        all_fields = set()
        for af in add_fields_stages:
            all_fields.update(af.keys())
        assert "payment_value" in all_fields

    def test_pc_lookup_filters_approved_and_paid_only(self):
        pipeline = build_payment_value_pipeline(PROJECT_ID)
        lookups = [s["$lookup"] for s in pipeline if "$lookup" in s]
        pc_lookup = next(lk for lk in lookups if lk["from"] == "payment_certificates")
        sub_match = next(s["$match"] for s in pc_lookup["pipeline"] if "$match" in s)
        expr = sub_match["$expr"]["$and"]
        status_filter = next(cond for cond in expr if "$in" in cond)
        assert status_filter["$in"][1] == PC_APPROVED_STATUSES
        # Verify "Approved" and "Paid" are specifically included
        assert "Approved" in PC_APPROVED_STATUSES
        assert "Paid" in PC_APPROVED_STATUSES


class TestParentRollupStructure:
    """Verify rollup pipeline groups by parent_id."""

    def test_has_group_stage(self):
        pipeline = build_parent_rollup_pipeline(PROJECT_ID)
        stage_keys = [list(s.keys())[0] for s in pipeline]
        assert "$group" in stage_keys

    def test_group_by_parent_id(self):
        pipeline = build_parent_rollup_pipeline(PROJECT_ID)
        group_stage = next(s["$group"] for s in pipeline if "$group" in s)
        assert group_stage["_id"] == "$parent_id"

    def test_rollup_includes_parent_wo_value(self):
        pipeline = build_parent_rollup_pipeline(PROJECT_ID)
        group_stage = next(s["$group"] for s in pipeline if "$group" in s)
        assert "parent_wo_value" in group_stage

    def test_rollup_includes_parent_payment_value(self):
        pipeline = build_parent_rollup_pipeline(PROJECT_ID)
        group_stage = next(s["$group"] for s in pipeline if "$group" in s)
        assert "parent_payment_value" in group_stage

    def test_only_leaf_tasks_grouped(self):
        """parent_id must not be None — only tasks WITH parents are grouped."""
        pipeline = build_parent_rollup_pipeline(PROJECT_ID)
        match_stage = next(s["$match"] for s in pipeline if "$match" in s)
        assert match_stage["parent_id"] == {"$ne": None}


# =============================================================================
# In-memory computation tests (no DB required)
# =============================================================================

class TestCostVarianceFlag:
    """Constitution §2.3: cost_variance flag computation."""

    def test_overrun_when_wo_exceeds_baseline(self):
        assert compute_cost_variance_flag(Decimal("100")) == "overrun"

    def test_underrun_when_baseline_exceeds_wo(self):
        assert compute_cost_variance_flag(Decimal("-50")) == "underrun"

    def test_on_budget_when_zero(self):
        assert compute_cost_variance_flag(Decimal("0")) == "on_budget"

    def test_small_positive_is_overrun(self):
        assert compute_cost_variance_flag(Decimal("0.01")) == "overrun"

    def test_small_negative_is_underrun(self):
        assert compute_cost_variance_flag(Decimal("-0.01")) == "underrun"


class TestWeightagePercent:
    """Schema §2.3: weightage = (baseline_cost / project_total) * 100"""

    def test_basic_weightage(self):
        result = compute_weightage_percent(Decimal("500"), Decimal("1000"))
        assert result == Decimal("50.00")

    def test_full_weight(self):
        result = compute_weightage_percent(Decimal("1000"), Decimal("1000"))
        assert result == Decimal("100.00")

    def test_zero_total_returns_zero(self):
        result = compute_weightage_percent(Decimal("100"), Decimal("0"))
        assert result == Decimal("0")

    def test_none_baseline_cost_returns_zero(self):
        result = compute_weightage_percent(None, Decimal("1000"))
        assert result == Decimal("0")

    def test_precision_two_decimal_places(self):
        # 1 / 3 * 100 = 33.33...
        result = compute_weightage_percent(Decimal("1"), Decimal("3"))
        assert str(result) == "33.33"


# =============================================================================
# Approved status constants tests
# =============================================================================

class TestApprovedStatusConstants:
    """Verify the approved status lists include the required values per spec."""

    def test_wo_approved_statuses_include_approved(self):
        assert "Approved" in WO_APPROVED_STATUSES

    def test_wo_approved_statuses_include_completed(self):
        assert "Completed" in WO_APPROVED_STATUSES

    def test_pc_approved_statuses_include_approved(self):
        assert "Approved" in PC_APPROVED_STATUSES

    def test_pc_approved_statuses_include_paid(self):
        """Schema §2.2: payment_value = sum of 'Approved' and 'Paid' certificates."""
        assert "Paid" in PC_APPROVED_STATUSES

    def test_draft_wo_not_included(self):
        assert "Draft" not in WO_APPROVED_STATUSES

    def test_pending_pc_not_included(self):
        assert "Pending" not in PC_APPROVED_STATUSES
