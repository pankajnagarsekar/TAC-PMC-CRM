# CRM Financial Calculation Engine Specification (STRICT – NO COMPROMISE)
## Version 1 – Authoritative Calculation Logic
Generated: 2026-03-18

---

# 1. CORE PRINCIPLES

1. Entire system operates PER PROJECT.
2. Two independent financial models:
   - Commitment Model (WO driven)
   - Liquidity Model (Petty / OVH driven)
3. All monetary values use DECIMAL(18,2) with ROUND_HALF_UP.
4. No floating point allowed.
5. All calculations are backend authoritative.

---

# 2. MASTER BUDGET STRUCTURE

For each category:

original_budget (fixed unless manually edited upward)
committed_amount (sum of WO grand_total)
remaining_budget = original_budget - committed_amount

remaining_budget CAN BE NEGATIVE (warning only)

Master Budget:

master_original_budget = SUM(original_budget for all categories)
master_remaining_budget = SUM(remaining_budget for all categories)

---

# 3. WORK ORDER (WO) CALCULATIONS

## 3.1 Constraints

- One WO = One Category
- WO can exceed remaining budget (warning only)
- WO editable unless violates PC constraints

---

## 3.2 Line Items

total = ROUND(qty × rate, 2)

---

## 3.3 WO Totals

subtotal = SUM(line totals)

total_before_tax = subtotal - discount

cgst_amount = total_before_tax × (cgst_percent / 100)

sgst_amount = total_before_tax × (sgst_percent / 100)

grand_total = total_before_tax + cgst_amount + sgst_amount

retention_amount = grand_total × (retention_percent / 100)

total_payable = grand_total

actual_payable = grand_total - retention_amount

---

## 3.4 Budget Impact (CRITICAL)

On WO CREATE:

committed_amount += grand_total

On WO UPDATE:

committed_amount = SUM(all WO grand_total for category)

remaining_budget recalculated

master_remaining_budget recalculated

On WO DELETE:

committed_amount recalculated

---

## 3.5 Restrictions

IF WO status = Closed:
- Cannot reduce WO below SUM(PC grand_total linked to WO)

---

# 4. PAYMENT CERTIFICATE (PC) CALCULATIONS

## 4.1 PC Types

TYPE 1: WO-linked PC
TYPE 2: Petty/OVH PC (no WO)

---

## 4.2 Line Items

total = ROUND(qty × rate, 2)

---

## 4.3 PC Totals

subtotal = SUM(line totals)

retention_amount = subtotal × (retention_percent / 100)

total_after_retention = subtotal - retention_amount

cgst_amount = total_after_retention × (cgst_percent / 100)

sgst_amount = total_after_retention × (sgst_percent / 100)

grand_total = total_after_retention + cgst_amount + sgst_amount

---

## 4.4 WO-Linked PC Behavior

On PC SAVE:
vendor_total_payable += grand_total
vendor_retention += retention_amount

On PC CLOSE:
vendor_total_payable -= grand_total

Constraint:

SUM(PC grand_total for WO) > WO grand_total:
→ WARNING ONLY (no block)

---

# 5. PETTY CASH / OVH (LIQUIDITY MODEL)

## 5.1 Definitions

allocation_original = category budget set in project

allocation_received = total money received from client

allocation_remaining = allocation_original - allocation_received

allocation_remaining CANNOT be negative

cash_in_hand = allocation_received - total_expenses

cash_in_hand CAN be negative

total_expenses = SUM(all expense logs)

---

## 5.2 PC (Fund Request) Behavior

On PC CREATE:
(no financial impact)

On PC CLOSE:

allocation_received += grand_total

allocation_remaining = allocation_original - allocation_received

master_remaining_budget -= grand_total

cash_in_hand += grand_total

last_pc_closed_date = current_date

---

## 5.3 Expense Entry

On expense log:

cash_in_hand -= expense_amount

total_expenses += expense_amount

NOTE:
- Does NOT affect master budget
- Does NOT affect allocation_remaining

---

## 5.4 Threshold Logic

IF cash_in_hand <= threshold:
→ notify admin

Timer = current_date - last_pc_closed_date

Timer resets ONLY on PC CLOSE

---

## 5.5 Constraint

IF allocation_remaining == 0:
→ PC creation NOT allowed

---

# 6. CSA CATEGORY

CSA behaves EXACTLY like normal category:

- Included in master budget
- Uses commitment model
- WO deducts budget
- No liquidity logic

---

# 7. NEGATIVE RULES

remaining_budget → CAN be negative
cash_in_hand → CAN be negative
allocation_remaining → CANNOT be negative

---

# 8. GLOBAL RECALCULATION RULES

Any update must trigger recalculation:

- WO create/update/delete → update committed_amount
- PC close (Petty/OVH) → update allocation + master budget
- Expense log → update cash_in_hand
- Budget edit → must not go below committed_amount

---

# 9. FINANCIAL INVARIANTS (MANDATORY)

1. committed_amount = SUM(WO grand_total per category)
2. remaining_budget = original_budget - committed_amount
3. master_remaining_budget = SUM(category remaining_budget)
4. allocation_remaining = allocation_original - allocation_received
5. cash_in_hand = allocation_received - total_expenses
6. Vendor payable:
   = SUM(PC created) - SUM(PC closed)

---

# 10. ROUNDING

ALL calculations:
ROUND(value, 2)

---

# END OF STRICT CALCULATION SPEC
