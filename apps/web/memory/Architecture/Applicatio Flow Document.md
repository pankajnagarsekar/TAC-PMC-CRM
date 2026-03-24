# Application Flow Document

## CRM Financial Management System -- Version 2.0 (Monorepo Ecosystem)

**Document 2 of 6** **Generated On:** 04 March 2026

------------------------------------------------------------------------

# 1. System Entry & Omnichannel Routing

## 1.1 Authentication
-   User logs in (Web or Mobile). System identifies Role (Admin, Supervisor, Client).
-   System loads Dashboard for selected project. If multiple projects exist, user selects project first.
-   System is always **Project Context Driven** after selection.

## 1.2 Client Read-Only Routing
-   If Role = Client: System fetches `GlobalSettings.client_permissions`.
-   Navigation menus and screens are dynamically filtered based on these booleans (e.g., `can_view_dpr`, `can_view_financials`).
-   All edit/save/delete buttons are stripped from the UI.

------------------------------------------------------------------------

# 2. Client & Project Setup Flow (Admin Web)

1.  **Client Creation:** Navigate to Client Module. Enter Name, Address, GSTIN, etc. Save.
2.  **Project Creation:** Select Client → Create Project. Enter Name, Code, Thresholds.
3.  **Budgeting:** System displays Categories. Admin enters Original Budget for each. Master Budget auto-calculated.
4.  **Save:** Project financial engine initialized. Audit log created.

------------------------------------------------------------------------

# 3. Work Order (WO) Flow (Admin Web)

1.  Navigate to WO Module → Create WO.
2.  Auto-generate WO Reference. Select Category (One WO = One Category).
3.  Select Vendor. Fill AG Grid (Excel-style): Sr No, Description, Qty, Rate.
4.  Apply Discount, CGST/SGST, and Retention %. 
5.  **Save (Pessimistic):** System initiates MongoDB Transaction. Category Remaining & Master Remaining reduced. Audit log created. If exceeds budget → Warning shown.

------------------------------------------------------------------------

# 4. Payment Certificate (PC) Flow (Admin Web)

## 4.1 Mode A: WO-Linked PC
1.  Select WO Reference. Category & Vendor auto-derived.
2.  Fill AG Grid for certified work. Subtotal, Retention, and Grand Total calculated.
3.  **Save:** Vendor Payable increases. Audit log recorded.

## 4.2 Mode B: Petty / OVH PC (Fund Request)
1.  Leave WO blank. Select Category (Petty or OVH). Fill grid.
2.  **Save:** Tagged as fund-request PC. No vendor payable update.

## 4.3 Close PC
-   **If WO-Linked:** Vendor payable reduces. Payment complete.
-   **If Petty/OVH:** Remaining Allocation reduces. Master Remaining reduces. Cash in Hand increases. 15-day countdown timer resets.

------------------------------------------------------------------------

# 5. Petty Cash & OVH Flow (Admin Mobile + Web)

1.  **Mobile Field Entry:** Admin opens Mobile App → Petty Cash Module.
2.  Enter Amount, Bill/Invoice Photo, Description.
3.  **Save:** Cash in Hand reduces instantly. 
4.  **Threshold Trigger:** If Cash in Hand ≤ Threshold, UI displays persistent Amber warning. If negative, text turns Red. 
5.  **Sync:** Web CRM dashboard updates instantly via backend recalculation.

------------------------------------------------------------------------

# 6. Site Operations & DPR Flow (Mobile → Web)

## 6.1 Supervisor Entry (Mobile)
1.  Supervisor submits Worker Attendance (GPS/Selfie), Voice Logs, and Daily Progress Report (DPR) with photos.
2.  Status set to `DRAFT` or `PENDING_APPROVAL`.

## 6.2 Admin Approval (Web CRM)
1.  Admin navigates to "Site Operations" module on Web CRM.
2.  Admin reviews Attendance anomalies, transcribes/listens to Voice Logs, and reviews DPR details.
3.  Admin clicks "Approve". Status updates to `APPROVED`.

## 6.3 Client Visibility
-   If `GlobalSettings.client_permissions.can_view_dpr` is True, Client sees the `APPROVED` DPR on their Mobile App and Web Portal.

------------------------------------------------------------------------

# 7. Reports & Export Flow

1.  Select Report Type (Project Summary, WO Tracker, Petty Tracker, etc.).
2.  System aggregates data strictly from MongoDB backend (No frontend math).
3.  User clicks Export. 
4.  **ExcelJS** injects data into strict templates. **Puppeteer** generates PDF mimicking the Excel layout exactly. T&C appended to final page.

------------------------------------------------------------------------
**End of Application Flow Document -- Version 2.0 Locked**