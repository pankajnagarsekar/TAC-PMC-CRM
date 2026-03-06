"""
MongoDB Index Definitions.
Run ensure_indexes(db) at startup to create all required compound/unique indexes.
"""
import logging

logger = logging.getLogger(__name__)


async def ensure_indexes(db) -> None:
    """
    Create all required MongoDB indexes for performance and data integrity.
    """
    async def safe_create_index(collection, keys, **kwargs):
        try:
            await collection.create_index(keys, **kwargs)
        except Exception as e:
            # Code 85 is IndexOptionsConflict
            if getattr(e, 'code', None) == 85:
                # Find the index with the same keys to drop it
                async for index in collection.list_indexes():
                    if index['key'] == dict(keys):
                        logger.warning(f"Dropping conflicting index '{index['name']}' in {collection.name}")
                        await collection.drop_index(index['name'])
                        break
                # Retry creation
                await collection.create_index(keys, **kwargs)
            else:
                logger.error(f"Failed to create index on {collection.name}: {str(e)}")
                raise

    # ── Project Category Budgets ─────────────────────────────────────────
    await safe_create_index(
        db.project_budgets,
        [("project_id", 1), ("code_id", 1)],
        unique=True,
        name="idx_budget_project_code"
    )

    # ── Work Orders ──────────────────────────────────────────────────────
    await safe_create_index(
        db.work_orders,
        [("project_id", 1), ("category_id", 1)],
        name="idx_wo_project_category"
    )
    await safe_create_index(
        db.work_orders,
        [("wo_ref", 1)],
        unique=True,
        name="idx_wo_ref_unique"
    )
    await safe_create_index(
        db.work_orders,
        [("project_id", 1), ("status", 1)],
        name="idx_wo_project_status"
    )

    # ── Payment Certificates ─────────────────────────────────────────────
    await safe_create_index(
        db.payment_certificates,
        [("project_id", 1), ("category_id", 1)],
        name="idx_pc_project_category"
    )
    await safe_create_index(
        db.payment_certificates,
        [("project_id", 1), ("work_order_id", 1)],
        name="idx_pc_project_wo"
    )

    # ── Cash Transactions ────────────────────────────────────────────────
    await safe_create_index(
        db.cash_transactions,
        [("project_id", 1), ("category_id", 1)],
        name="idx_cash_project_category"
    )

    # ── Vendor Ledger ────────────────────────────────────────────────────
    await safe_create_index(
        db.vendor_ledger,
        [("vendor_id", 1), ("project_id", 1)],
        name="idx_ledger_vendor_project"
    )

    # ── Operation Logs (Idempotency) ─────────────────────────────────────
    await safe_create_index(
        db.operation_logs,
        [("operation_key", 1)],
        unique=True,
        name="idx_oplog_key_unique"
    )

    # ── Vendors ──────────────────────────────────────────────────────────
    await safe_create_index(
        db.vendors,
        [("organisation_id", 1), ("active_status", 1)],
        name="idx_vendor_org_active"
    )

    # ── Fund Allocations ─────────────────────────────────────────────────
    await safe_create_index(
        db.fund_allocations,
        [("project_id", 1), ("category_id", 1)],
        unique=True,
        name="idx_fund_project_category"
    )

    # ── Audit Logs ───────────────────────────────────────────────────────
    await safe_create_index(
        db.audit_logs,
        [("entity_type", 1), ("entity_id", 1)],
        name="idx_audit_entity"
    )
    await safe_create_index(
        db.audit_logs,
        [("created_at", -1)],
        name="idx_audit_created"
    )

    logger.info("All MongoDB indexes ensured successfully.")
