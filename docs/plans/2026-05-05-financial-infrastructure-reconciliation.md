# Financial Infrastructure Reconciliation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reconcile and implement the financial core logic, categories, and UI/UX requirements for Work Orders (WO), Payment Certificates (PC), and Site Funds (Petty Cash/OVH) to align with the "Notebook Truth".

**Architecture:** 
- **Data Layer:** Seed 14 mandatory categories via MongoDB.
- **Service Layer:** `FinancialService` and `CashService` handle calculations (discount before tax, retention before tax, 15-day replenishment timer).
- **Frontend Layer:** React components with "Excel-style" grids and header/footer fields matching the exact specs.

**Tech Stack:** React 19, FastAPI, MongoDB, Tailwind 4.

---

### Task 1: Seed 14 Mandatory Application-Wide Categories

**Files:**
- Modify: `apps/api/scripts/seed_codes.py`

**Step 1: Update the categories list**
Update `default_codes` in `seed_codes.py` to include:
- CIV (Civil Works)
- PLB (Plumbing Works)
- ELC (Electrical Works)
- SWP (Swimming Pool Works)
- HVC (HVAC / Air Conditioning)
- FIN (Finishing Works)
- CRP (Carpentry / Fixed)
- LAN (Landscaping & External Works)
- EQP (Equipments & Special System)
- PRF (Professional Fees)
- STC (Approvals & Statutory Charges)
- OVH (Site Overheads / Running Expenses)
- CSA (Client Supplied Assets)
- CON (Contingency)

**Step 2: Run the seed script**
Run: `python apps/api/scripts/seed_codes.py`
Expected: 14 categories seeded/updated in `code_masters` collection.

**Step 3: Commit**
```bash
git add apps/api/scripts/seed_codes.py
git commit -m "feat(financial): seed 14 mandatory application-wide categories"
```

### Task 2: Update Work Order (WO) DTOs and Validation

**Files:**
- Modify: `apps/api/app/modules/contracting/schemas/dto.py`
- Modify: `apps/api/app/modules/financial/domain/engine.py` (Verify/Update calculation logic)

**Step 1: Update `WorkOrder` and `WOLineItem` schemas**
Add mandatory fields:
- Header: `issued_by`, `shipping_to`, `warranty_product`, `warranty_workmanship`, `terms_and_conditions`.
- Calculations: Ensure `subtotal`, `discount_value`, `total_before_tax`, `cgst_value`, `sgst_value`, `grand_total`.

**Step 2: Update `FinancialEngine` calculation logic**
Ensure:
1. `Total = Subtotal - Discount`
2. `Grand Total = Total + CGST + SGST`
(Discount is applied *before* tax).

**Step 3: Commit**
```bash
git add apps/api/app/modules/contracting/schemas/dto.py apps/api/app/modules/financial/domain/engine.py
git commit -m "feat(financial): update WO schemas and discount-before-tax logic"
```

### Task 3: Update Payment Certificate (PC) DTOs and Validation

**Files:**
- Modify: `apps/api/app/modules/financial/schemas/dto.py`

**Step 1: Update `PaymentCertificate` schema**
Add mandatory fields:
- Header: `pc_refn` (auto-incremented), `contractor_category`, `gst_number` (auto-populates).
- Grid: `Sr. No`, `Scope of work`, `rate`, `qty`, `unit`, `total`.
- Footer: `pmc_comments`, `retention_percentage`, `retention_amount`, `total_after_retention`, `cgst_value`, `sgst_value`, `grand_total`.

**Step 2: Update calculation logic**
Ensure:
1. `Total = Subtotal - Retention`
2. `Grand Total = Total + CGST + SGST`
(Retention is applied *before* tax).

**Step 3: Commit**
```bash
git add apps/api/app/modules/financial/schemas/dto.py
git commit -m "feat(financial): update PC schemas and retention-before-tax logic"
```

### Task 4: Implement 15-Day Replenishment Timer Logic

**Files:**
- Modify: `apps/api/app/modules/financial/application/cash_service.py`

**Step 1: Update `get_cash_summary` logic**
- Calculate `replenishment_timer_days` = `15 - (days since last_pc_created_at)`.
- Ensure it resets when the PC is closed or cash is received.
- Distinguish between `PETTY` and `OVH` timers.

**Step 2: Commit**
```bash
git add apps/api/app/modules/financial/application/cash_service.py
git commit -m "feat(financial): implement 15-day backward replenishment timer for Site Funds"
```

### Task 5: Implement "Heavy Excel Style" UI for WO and PC

**Files:**
- Modify: `apps/mobile/app/(admin)/contracting/work-orders/new.tsx`
- Modify: `apps/mobile/app/(admin)/financial/payment-certificates/new.tsx`

**Step 1: Implement Grid Data Entry**
- Use a spreadsheet-like grid for line items (Sr. No, Description, Qty, Rate, Total).
- Add header fields: `Issued by`, `Shipping to`, `Warranty`, etc.
- Add footer fields: `Discount`, `Retention`, `CGST`, `SGST`.

**Step 2: Commit**
```bash
git add apps/mobile/app/(admin)/contracting/work-orders/new.tsx apps/mobile/app/(admin)/financial/payment-certificates/new.tsx
git commit -m "feat(ui): implement excel-style grid for WO and PC"
```

### Task 6: Implement CSA (Client Supplied Assets) Tracker

**Files:**
- Create: `apps/mobile/app/(admin)/financial/csa/tracker.tsx`

**Step 1: Implement CSA Manager Screen**
- Columns: `Category code`, `WO Reference`, `Description`, `Quantity`, `Received Date`.
- Header: `Project name`, `Client name`, `Date`.
- Allow logging physical assets linked to WOs created under CSA category.

**Step 2: Commit**
```bash
git add apps/mobile/app/(admin)/financial/csa/tracker.tsx
git commit -m "feat(ui): add CSA asset tracking screen"
```

### Task 7: Dashboard Verification & Replenishment Timers

**Files:**
- Modify: `apps/mobile/app/(admin)/dashboard/index.tsx`

**Step 1: Add Countdown Timers**
- Display separate 15-day countdowns for Petty Cash and OVH.
- Use Red color for negative balances or expired timers.

**Step 2: Commit**
```bash
git add apps/mobile/app/(admin)/dashboard/index.tsx
git commit -m "feat(ui): display site fund replenishment timers on dashboard"
```

### Task 8: Verification and Linting

**Step 1: Run Linting**
Run: `pnpm lint`

**Step 2: Run Backend Tests**
Run: `pnpm -C apps/api exec python -m pytest`

**Step 3: Verify Alignment with Notebook**
Perform manual walkthrough of UI fields against `notebooklm.md` requirements.

**Step 4: Commit**
```bash
git commit -m "chore: final verification and linting for financial reconciliation"
```
