# Enterprise Frontend Engineering Specification

## CRM Financial Management System -- Version 2.0 (Web & Mobile Parity)

**Document 4 of 6 -- Upgraded Precision Version** **Generated On:** 04 March 2026

------------------------------------------------------------------------

# 1. Frontend Engineering Mandate

Both the Next.js Web CRM and Expo Mobile App must operate as **deterministic financial interfaces**. 

They must:
-   Reflect backend financial truth without deviation.
-   Prevent arithmetic drift.
-   Prevent inconsistent state transitions.
-   Handle concurrent updates safely.
-   Be Excel-faithful in structure and UX (Web).
-   Scale to large datasets.
-   Be version-conflict aware.
-   Be visually explicit about warnings without blocking allowed financial actions.

**No silent UI assumptions permitted. Shared TypeScript types (`/packages/types`) must dictate all data structures.**

------------------------------------------------------------------------

# 2. Project Context Enforcement & State

## 2.1 Mandatory Project Lock
After login, whether on Web or Mobile:
-   User must select a Project.
-   Project ID is stored in global state (e.g., Zustand or React Context).
-   All API calls must inject this Project ID.
-   Switching a project instantly purges all state trees and cached API data (SWR/React Query) to prevent cross-project data mixing.

## 2.2 Global State Layers
1.  Auth State & JWT payload (Role identification)
2.  Project Context State
3.  Financial Snapshot State (Dashboard)
4.  Active Transaction State (WO/PC forms)
5.  Report Filter State
6.  Timer State (Petty/OVH)
7.  Version Control Metadata

------------------------------------------------------------------------

# 3. Optimistic vs Pessimistic Updates

All financial writes use **Pessimistic Update Strategy**:
1.  User clicks Save.
2.  Button enters disabled/loading state (skeleton or sleek micro-animation).
3.  Await FastAPI MongoDB transaction confirmation.
4.  Replace UI totals exclusively with backend authoritative totals.
5.  Never assume success until server responds.

------------------------------------------------------------------------

# 4. Web CRM: AG Grid Excellence (Strict)

All financial grids in the Web CRM must use AG Grid (Enterprise) themed with Tailwind CSS to match the modern "Fintech" aesthetic.

## 4.1 Mandatory Grid Capabilities
-   Keyboard-only navigation
-   Inline validation
-   Row locking after save (if required by status)
-   Manual total field (validated against Qty * Rate)
-   Two-decimal formatting strictly aligned to the right (using commas and the ₹ symbol).
-   Column resizing and copy-paste behavior.
-   Row number auto-increment.

## 4.2 Line Item Validation Matrix
For each row:
-   `Qty > 0`
-   `Rate ≥ 0`
-   Total must equal `Qty * Rate` (rounded to 2 decimals).
-   If mismatch → Row is marked invalid, and Save is blocked. 
Backend recalculates regardless.

------------------------------------------------------------------------

# 5. Admin Mobile UX: Petty Cash & OVH (Precision Rules)

The Mobile App provides Admins with high-speed financial entry tools while adhering to strict Fund-Transfer logic.

## 5.1 Cash-In-Hand Display
-   If value < 0 → render text in bold Red (`#EF4444`) with a warning icon.
-   Include a tooltip/modal explaining the negative state.
-   Do not block entry.

## 5.2 Threshold Alerts
-   If Cash ≤ Threshold, display a persistent Amber alert banner.
-   Provide a quick "Create PC" button for fund replenishment.

## 5.3 Countdown Timer Logic
Timer = Today - LastPCClosedDate

Color rules:
-   0–10 days → Normal
-   11–14 days → Amber
-   15+ days → Red

Timer recalculated every minute client-side but strictly validated server-side.

------------------------------------------------------------------------

# 6. Client Read-Only Presentation Layer (Omnichannel)

When the JWT payload identifies the user role as `Client`:
1.  Fetch `GlobalSettings.client_permissions` from the backend.
2.  **Dynamic Rendering:** Dynamically mount/unmount Sidebar routes (e.g., Hide "Financials" entirely if `can_view_financials` is False).
3.  **Input Disablement:** Disable all inputs, AG Grid edit capabilities, and form submission buttons.
4.  **Presentation Focus:** Optimize UI for presentation. Focus on Tremor.so charts, high-level health summaries, and the Approved DPR Photo Galleries.
5.  **Export Controls:** Provide a prominent "Export to PDF" button on all visible screens that generates branded, letterhead-style documents.

------------------------------------------------------------------------

# 7. Web CRM: Site Operations Dashboard Parity

The Web CRM must have a dedicated view to manage and approve all mobile-generated field data:
* **DPR Review:** Gallery view of site photos, notes, and progress deltas. Includes an explicit "Approve" button to transition the document state.
* **Attendance Verification:** Grid displaying worker names, selfies, GPS coordinate map links, and check-in timestamps.
* **Voice Logs:** Custom audio player component paired with a text block displaying the backend-transcribed text.

------------------------------------------------------------------------

# 8. Error Handling & Version Conflicts

## 8.1 Concurrency Conflict UX
If editable entities (WO, PC, Budget) have a version mismatch on save (backend responds with concurrency error):
-   Show a blocking modal explaining the record was updated by another session.
-   Provide a reload option to fetch the latest state.
-   Never silently overwrite.

## 8.2 General Errors
-   Financial validation errors: Show specific field errors returned by the FastAPI backend.
-   Network errors: Show retry option.
-   Duplicate submission blocked via request lock (Idempotency Key must be tracked in frontend state during the request cycle).
-   All errors logged client-side (non-sensitive).

------------------------------------------------------------------------

# 9. Accessibility & Determinism

-   All numeric fields right-aligned.
-   Currency formatted strictly to 2 decimals.
-   Keyboard navigation mandatory across Web CRM grids.
-   No hidden financial values.
-   No auto-rounding discrepancies (Rely entirely on backend `Decimal128` results).

------------------------------------------------------------------------

# Conclusion

Frontend is a deterministic financial interface layer that:
-   Mirrors Excel precision via AG Grid.
-   Enforces state consistency across a Monorepo ecosystem.
-   Handles MongoDB transactional concurrency safely.
-   Reflects backend financial truth without mutation.
-   Provides dynamic Omnichannel presentation layers.

No UI behavior may compromise financial precision.

------------------------------------------------------------------------

**End of Enterprise Frontend Engineering Specification -- Version 2.0 Locked**