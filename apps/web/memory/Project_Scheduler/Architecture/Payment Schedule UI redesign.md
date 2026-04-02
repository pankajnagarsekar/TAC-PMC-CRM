Final Route Architecture
/admin/
├── dashboard/                      ← Enhanced (+ Mini Gantt, + KPI Cards)
│
├── scheduler/                      ← "Project Planner" — TABBED, replaces single-scroll page
│   ├── ?tab=grid      (default)    ← Master Grid + Task Drawer slide-in
│   ├── ?tab=gantt                  ← Full Gantt Chart + Dependency Overlay
│   ├── ?tab=kanban                 ← Full Kanban Board
│   ├── ?tab=s-curve                ← S-Curve & Earned Value Analysis
│   ├── ?tab=cash-flow              ← Cash Flow Forecast
│   ├── ?tab=resources              ← Resource Heatmap
│   ├── ?tab=budget                 ← Budget vs. Actuals
│   └── ?tab=export                 ← Export Center (PDF / Import / Migrate)
│
├── reports/                        ← UNCHANGED — Financial Intelligence
│   └── (project_summary, WO tracker, PC tracker, Petty Cash, etc.)
│
└── ... (all other pages unchanged)
Page-by-Page Specification
Page 1: /admin/dashboard — 3 Changes
Add:

✅ Mini Gantt (

PortfolioGantt
 component already built) — shows 6-month milestone timeline in Column 2, replacing the static "Construction Schedule" bar chart
✅ KPI Cards strip (Total Baseline, Planner Value, EV, AC, SPI, CPI) — added as a full-width row at the top of the dashboard after the project context bar
✅ A "→ View Full Planner" link button on the Gantt widget that navigates to /admin/scheduler?tab=gantt
Remove from scheduler (goes here):

KPI Cards row
Keep everything else as-is.

Page 2: /admin/scheduler — Complete Redesign (Tab Architecture)
Header: Project Planner title + toolbar (unchanged)

Below header: An 8-tab horizontal tab bar:

[ Grid ]  [ Gantt ]  [ Kanban ]  [ S-Curve ]  [ Cash Flow ]  [ Resources ]  [ Budget ]  [ Export ]
Tab	Content	Width
Grid (default)	

SchedulerGrid
 (full width) + TaskDrawer slides from right, no overlap	Full
Gantt	GanttChart + GanttDependencyOverlay full canvas with zoom controls	Full
Kanban	KanbanBoard full width, 5 columns	Full
S-Curve	SCurveChart full-size + EV/PV/AC legend	Full
Cash Flow	CashFlowChart full-size + threshold alert indicators	Full
Resources	ResourceHeatmap full-size + legend	Full
Budget	FinancialChart (Budget vs Actuals per category, already on dashboard)	Full
Export	Import (.mpp/XML), Export PDF, Migrate Legacy — currently in toolbar, moved here as a clean page	Full
Removed from main scheduler view:

❌ KPI Cards strip → Dashboard
❌ Bottom section with CashFlow + Heatmap stacked → moved to dedicated tabs
❌ Active Scheduler Directives banner → collapsed into an info icon tooltip
Page 3: /admin/reports — No Changes
This is already a working, separate Financial Intelligence system (Project Summary, WO Tracker, PC Tracker, Petty Cash, CSA, Attendance, DPR). This page stays exactly as-is.

Client Role — Same Pages, Filtered Nav
The Sidebar already has client_permissions.can_view_reports filtering. The plan:

What Clients See	Config
Dashboard (with Mini Gantt + KPI Cards)	Always visible
Project Scheduler (read-only all tabs)	Add can_view_scheduler permission flag
Reports	Controlled by existing can_view_reports flag
All data-entry tabs (Grid/Kanban)	Read-only enforced (buttons hidden) per existing Frontend Spec §3
Note: The systemState === "locked" logic is already in 

SchedulerGrid
 — it disables all editing when locked, which maps perfectly to the Client read-only requirement.

Sidebar Changes (Minimal)
diff
- { label: "Project Scheduler", href: "/admin/scheduler" }
+ { label: "Project Planner", href: "/admin/scheduler", children: [
+   { label: "Grid",       href: "/admin/scheduler?tab=grid" },
+   { label: "Gantt",      href: "/admin/scheduler?tab=gantt" },
+   { label: "Kanban",     href: "/admin/scheduler?tab=kanban" },
+   { label: "Analytics",  href: "/admin/scheduler?tab=s-curve" },
+   { label: "Export",     href: "/admin/scheduler?tab=export" },
+ ]}
What Gets Built / Modified (File List)
File	Action

apps/web/src/app/admin/scheduler/page.tsx
Rewrite — tab architecture

apps/web/src/app/admin/dashboard/page.tsx
Modify — add KPI row + swap to PortfolioGantt

apps/web/src/components/layout/Sidebar.tsx
Modify — rename + add sub-items

apps/web/src/components/dashboard/KPICards.tsx
Reuse — no change needed

apps/web/src/components/dashboard/PortfolioGantt.tsx
Reuse — no change needed
All other scheduler components	Reuse — no change needed

apps/web/src/app/admin/reports/page.tsx
No change
User Flow — Before vs After
BEFORE:  scheduler → endless scroll → all modules congested on one canvas
AFTER (Admin):
  Dashboard → KPIs + Mini Gantt (overview) → click "View Full Planner"
  Scheduler → pick tab: Grid (enter data) | Gantt | Kanban | S-Curve | etc.
AFTER (Client):
  Same Dashboard → read-only KPIs + Mini Gantt
  Scheduler → all tabs visible, all inputs disabled/hidden