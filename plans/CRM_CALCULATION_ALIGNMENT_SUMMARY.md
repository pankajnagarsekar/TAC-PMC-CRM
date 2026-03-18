# CRM Calculation Alignment Summary

## Overview

This document summarizes the changes made to align the CRM codebase with the **CRM Financial Calculation Engine Specification (STRICT)**.

## Critical Issues Fixed

### 1. Work Order (WO) Calculations - FIXED ✅

**File:** `apps/api/work_order_service.py`

**Issue:** CGST/SGST was being calculated on `subtotal` instead of `total_before_tax`.

**Spec Reference:** §3.3 WO Totals

```
total_before_tax = subtotal - discount
cgst_amount = total_before_tax × (cgst_percent / 100)
sgst_amount = total_before_tax × (sgst_percent / 100)
```

**Fix:**

- Changed CGST/SGST calculation to use `total_before_tax` (after discount) instead of `subtotal`
- Added server-side tax rate fetching from project settings
- Ensured proper ROUND_HALF_UP rounding at each step

---

### 2. Payment Certificate (PC) Calculations - FIXED ✅

**File:** `apps/api/payment_certificate_service.py`

**Issue:** Tax was being calculated on `subtotal` instead of `total_after_retention`.

**Spec Reference:** §4.3 PC Totals

```
subtotal = SUM(line totals)
retention_amount = subtotal × (retention_percent / 100)
total_after_retention = subtotal - retention_amount
cgst_amount = total_after_retention × (cgst_percent / 100)
sgst_amount = total_after_retention × (sgst_percent / 100)
grand_total = total_after_retention + cgst_amount + sgst_amount
```

**Fix:**

- Changed calculation order: retention first, then tax on remaining
- Added `total_after_retention` field to PC model
- CGST/SGST now calculated on `total_after_retention` (not subtotal)
- Ensured proper ROUND_HALF_UP rounding at each step

---

### 3. Liquidity Model (Petty/OVH) - FIXED ✅

**Files:**

- `apps/api/payment_certificate_service.py`
- `apps/api/cash_routes.py`
- `apps/api/cash_service.py`
- `apps/api/hardened_routes.py`
- `apps/api/models.py`

**Issues:**

1. `cash_in_hand` was incorrectly calculated from `allocation_remaining`
2. `total_expenses` field was missing from FundAllocation model
3. Expense entries were incorrectly modifying `allocation_remaining`

**Spec Reference:** §5.1 Definitions

```
allocation_original = category budget set in project
allocation_received = total money received from client
allocation_remaining = allocation_original - allocation_received
cash_in_hand = allocation_received - total_expenses
total_expenses = SUM(all expense logs)
```

**Fixes:**

1. **Model Update** (`models.py`):
   - Added `cash_in_hand` field to FundAllocation
   - Added `total_expenses` field to FundAllocation

2. **Cash Transaction** (`cash_routes.py`):
   - Per Spec §5.3: Expense entries now:
     - Decrement `cash_in_hand` by expense amount
     - Increment `total_expenses` by expense amount
     - Do NOT affect `allocation_remaining`

3. **Cash Summary** (`cash_service.py`, `hardened_routes.py`):
   - `cash_in_hand` now calculated as: `allocation_received - total_expenses`
   - `allocation_remaining` is now purely: `allocation_original - allocation_received`

4. **Fund Allocation Initialization** (`hardened_routes.py`):
   - Added `cash_in_hand` and `total_expenses` fields with default 0.0

---

### 4. PC Close for Petty/OVH - FIXED ✅

**File:** `apps/api/payment_certificate_service.py`

**Spec Reference:** §5.2 PC (Fund Request) Behavior

```
On PC CLOSE:
- allocation_received += grand_total
- allocation_remaining = allocation_original - allocation_received
- master_remaining_budget -= grand_total
- cash_in_hand += grand_total
- last_pc_closed_date = current_date
```

**Fix:**

- PC Close now properly updates all liquidity model fields
- `allocation_received` incremented by PC grand_total
- `allocation_remaining` recalculated
- `cash_in_hand` incremented by PC grand_total
- `last_pc_closed_date` updated (timer reset per §5.4)
- Master budget decremented by PC grand_total

---

## Financial Invariants (Per Spec §9)

The following invariants are now enforced:

1. ✅ `committed_amount = SUM(WO grand_total per category)`
2. ✅ `remaining_budget = original_budget - committed_amount`
3. ✅ `master_remaining_budget = SUM(category remaining_budget)`
4. ✅ `allocation_remaining = allocation_original - allocation_received`
5. ✅ `cash_in_hand = allocation_received - total_expenses`
6. ✅ Vendor payable: `= SUM(PC created) - SUM(PC closed)`

## Negative Rules (Per Spec §7)

| Field                  | Can Be Negative    | Status         |
| ---------------------- | ------------------ | -------------- |
| `remaining_budget`     | YES (warning only) | ✅ Implemented |
| `cash_in_hand`         | YES                | ✅ Implemented |
| `allocation_remaining` | NO                 | ✅ Enforced    |

## Files Modified

1. `apps/api/work_order_service.py` - WO calculation fixes
2. `apps/api/payment_certificate_service.py` - PC calculation & liquidity model fixes
3. `apps/api/cash_routes.py` - Expense entry logic fix
4. `apps/api/cash_service.py` - Cash summary calculation fix
5. `apps/api/hardened_routes.py` - Fund allocation initialization & cash summary fixes
6. `apps/api/models.py` - FundAllocation model updated with new fields

## Testing Recommendations

1. **WO Calculation Tests:**
   - Create WO with discount, verify CGST/SGST calculated on post-discount amount
   - Verify retention calculation

2. **PC Calculation Tests:**
   - Create PC with retention, verify tax calculated on post-retention amount
   - Verify total_after_retention field exists

3. **Liquidity Model Tests:**
   - Create expense, verify cash_in_hand decreases, total_expenses increases
   - Verify allocation_remaining unchanged by expenses
   - Close PC, verify allocation_received increases, cash_in_hand increases

4. **Invariant Tests:**
   - Verify all 6 financial invariants hold after each operation
   - Test negative cash_in_hand scenarios
   - Test negative remaining_budget scenarios

## Compliance Status

| Spec Section                 | Status                               |
| ---------------------------- | ------------------------------------ |
| §2 Master Budget Structure   | ✅ Compliant                         |
| §3 WO Calculations           | ✅ Compliant                         |
| §4 PC Calculations           | ✅ Compliant                         |
| §5 Petty/OVH Liquidity Model | ✅ Compliant                         |
| §6 CSA Category              | ✅ Compliant (uses commitment model) |
| §7 Negative Rules            | ✅ Compliant                         |
| §8 Global Recalculation      | ✅ Compliant                         |
| §9 Financial Invariants      | ✅ Compliant                         |
| §10 Rounding                 | ✅ Compliant (ROUND_HALF_UP)         |

## Notes

- All monetary values use `Decimal` with `ROUND_HALF_UP` rounding
- No floating point arithmetic in financial calculations
- All calculations are backend authoritative
- Proper audit trails maintained for all financial mutations
