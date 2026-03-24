# Directive: MSP-Style Project Scheduler & Financial Forecaster

## 1. Context & Purpose
This module replicates the functionality of Microsoft Project (MSP) within the TAC-PMC-CRM. It allows users to manually input or import project baselines (like TAC_Baseline_R0.pdf) and track them against real-time site data (like CIV_Rajesh_Tracking_14032026.pdf). It serves as the single source of truth for project timelines and financial outflows.

## 2. Goals & Deliverables
- **Interactive Grid:** A data entry interface identical to MSP (ID, Task Name, Duration, Start, Finish, Predecessors, Cost).
- **Dynamic Gantt Chart:** Visual representation of the timeline including progress bars and Critical Path.
- **Cash Flow Forecasting:** Automated report generation mapping "Task Cost" to "Finish Date" to project monthly/quarterly capital requirements.
- **High-Fidelity PDF Export:** Standardized reports including the Gantt chart for client distribution.

## 3. The 3-Layer Architecture

### Layer 1: Directive (Strategy)
- **Input:** Task definitions, durations, dependency links, and assigned costs.
- **Primary Tools:** scheduler_engine.py, financial_forecast.py, puppeteer_pdf_gen.py.
- **Constraints:** Must support a 6-day work week (standard for Goa construction) and flag any "Critical Path" delays.

### Layer 2: Orchestration (Intelligence)
- **Validation:** Check for circular dependencies (e.g., Task A depends on B, B depends on A).
- **Financial Alignment:** Cross-reference the "Cost" column with work_order_service.py to ensure the scheduled budget matches issued Work Orders.
- **Reporting Trigger:** Automatically regenerate the Cash Flow report whenever a major milestone date (e.g., "Slab Completion") is shifted.

### Layer 3: Execution (Deterministic Scripts)
- **execution/calculate_critical_path.py:** A Python script utilizing the Critical Path Method (CPM) to calculate Early Start/Finish and Late Start/Finish dates.
- **execution/generate_cash_report.py:** Aggregates costs from the ProjectSchedule MongoDB collection and formats them into a "Monthly Outflow Forecast".
- **execution/render_gantt_pdf.py:** A script that launches a headless browser to capture the React-based Gantt chart and save it as a PDF.

## 4. Operational SOPs
- **Data Entry:** Users must enter dates in DD-MM-YY format to maintain consistency with existing project files.
- **Predecessors:** Only "Finish-to-Start" (FS) relationships are supported in the initial version.
- **Error Handling:** If a task's "Actual Start" is entered before its predecessor is "100% Complete", the system must trigger a warning but allow the entry for manual oversight.

## 5. File & Directory Organization
- **Directives:** directives/project_scheduler.md
- **Execution Scripts:** execution/scheduler/
- **Intermediate Files:** .tmp/gantt_snapshot_{project_id}.png
- **Deliverables:** Google Drive / Project Folder (for PDF exports)
