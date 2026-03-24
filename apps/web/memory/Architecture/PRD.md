# Product Requirements Document (PRD)

## CRM Financial Management System -- Version 2.0 (Monorepo & MongoDB Enterprise Edition)

**Generated On:** 04 March 2026

------------------------------------------------------------------------

# 1. System Purpose

This CRM system is a structured digitization of an existing Excel-based financial management workflow used for construction project management. 

The system operates on a unified **Monorepo architecture**, featuring a **Next.js Web CRM (Admin Hub)** and an **Expo React Native Mobile App (Field & Reporting)**. It replicates Excel sheets structurally, visually, and functionally while introducing automation, validation, and reporting.

⚠ Architecture is locked. No redesign, simplification, or structural alteration is allowed. 
Entire system operates **per project**. Each project is financially independent.

------------------------------------------------------------------------

# 2. Core Financial Philosophy

The system operates on two financial models:

### 2.1 Commitment-Based Model
Used for normal categories (including CSA): 
- Work Order deducts from category budget immediately. 
- Master Remaining reduces instantly. 
- PC affects vendor payable but not category remaining.

### 2.2 Fund-Transfer-Based Model
Used for Petty Cash & OVH: 
- Budget reduces only when client funds are received (PC closed). 
- Expenses reduce Cash-in-Hand only. 
- Cash can go negative (display in red). 
- Threshold triggers notification. 
- 15-day countdown resets when PC is closed.

------------------------------------------------------------------------

# 3. Omnichannel Role & Access Matrix

Access is dynamically managed via the unified backend.

* **Admin:** Full read/write access to the Web CRM (Financials, Setup, Approvals). Full access to the Mobile App (Financial Dashboards, mobile Petty Cash/OVH entry).
* **Supervisor:** Mobile App only. Submits Daily Progress Reports (DPRs), Worker Attendance, Voice Logs, and requests Petty Cash. No global financial visibility.
* **Client (Omnichannel):** Access to both Web and Mobile. **Strictly Read-Only.** Screen and module visibility (e.g., viewing DPRs, Financial Dashboards, or static reports) is dynamically controlled by Admins via Global Settings.

------------------------------------------------------------------------

# 4. Master Budget Structure (Per Project)

Each Project contains multiple Categories.
Each Category has: 
- Original Budget (cannot be reduced downward) 
- Remaining Budget

Master Budget = Sum of all Original Category Budgets
Master Remaining = Sum of all Category Remaining Budgets

Categories include: Civil, Electrical, CSA (Client Supplied Assets), Petty Cash, OVH (Site Overheads / Running Expenses), and Others defined in Application-wide settings.
Single-category Work Order enforcement is mandatory.

------------------------------------------------------------------------

# 5. Module Definitions

## 5.1 Project & Client Setup Module (Web Only)
* **Client Creation:** Name, Address, Phone, Email, GSTIN.
* **Project Creation:** Project Name, Code, Select Client, Threshold Value (Petty & OVH).
* **Budgeting:** Admin enters Original Budget for each category. Master Budget auto-calculated.

## 5.2 Work Order (WO) Module (Web Only)
One WO = One Category only.
* **Deduction Logic:** When WO is created, deduct full amount from Category Remaining and Master Remaining. Budget never negative (warning only).
* **Lock Rule:** If WO is Closed, cannot reduce below generated PC total.
* **Grid (Excel-style mandatory):** Sr No, Description, Qty, Rate, Total. 
* **Footer:** Subtotal, Discount, Total, CGST, SGST, Grand Total, Retention %, Total Payable, Actual Payable.

## 5.3 Payment Certificate (PC) Module (Web Only)
Single UI for all PC creation.
* **Mode 1 (WO-Linked PC):** WO selected. Vendor payable affected. Category locked to WO.
* **Mode 2 (Petty/OVH PC):** No WO selected. Category selected (Petty/OVH). Treated as fund request.
* **Grid:** Sr No, Scope of Work, Rate, Qty, Unit, Total.
* **Footer:** Retention %, Retention Amount, Total Payable, CGST, SGST, Grand Total.

## 5.4 Petty Cash & OVH Module (Web & Admin Mobile)
* **Entry UI:** Available on Web and a specialized UI on the Admin Mobile App.
* **Logic:** Expense reduces Cash-in-Hand. Cash can go negative (red display). Threshold notification. 15-day countdown visible on dashboard. 
* **Funds Received:** Deduct Remaining Allocation and Master Remaining. Increase Cash-in-Hand. Reset timer.

## 5.5 Site Operations & DPR Module (Mobile → Web Parity)
* **Mobile Entry (Supervisors):** Vendor attendance (Selfie/GPS), Voice Logs, Site Progress, Photo uploads.
* **Web Review (Admins):** Admin Web CRM includes a dedicated "Site Operations" module to view, filter, and **Approve** all mobile-submitted logs and DPRs.
* **Client View:** Once approved, visible to Client (if permitted in Global Settings).

## 5.6 Reports & Dashboards Module (Web & Mobile)
* **Reports:** Project Summary, Weekly, 15 Days, Monthly, Custom Range, WO/PC Tracker, CSA Report.
* **Dashboards:** Master Budget & Remaining, Vendor Payables, Petty/OVH Cash status, 15-day countdowns, Over-budget alerts.
* All reports require Graph, PDF export, and Excel export (Template Engine).

## 5.7 Global Settings (Web Only)
* **Application-Wide:** Company Details, GST Rates, Company Logo, Default T&C, Category Master.
* **Client Permissions:** Admin toggle board to grant/revoke Client access to specific modules (DPRs, Financials, Dashboards) across Web and Mobile.

------------------------------------------------------------------------

# 6. Locked Constraints

-   No downward editing of category budgets.
-   Cannot raise Petty/OVH PC if Remaining Allocation = 0.
-   Cannot reduce WO below generated PC total.
-   Over-budget warning only (no hard stop).
-   Single-category WO enforcement.
-   Entire system operates independently per project.

------------------------------------------------------------------------
**End of PRD -- Version 2.0 Locked**