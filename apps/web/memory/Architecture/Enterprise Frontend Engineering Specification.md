# Enterprise Frontend Engineering Specification

## CRM Financial Management System — Version 3.0 (Precision Release)

**Document 4 of 6 — Technical Sovereignty Version**  
**Updated On:** 20 March 2026

---

# 1. Frontend Engineering Mandate

The Next.js Web CRM and Expo Mobile App must operate as **deterministic financial interfaces**. They are the authoritative presentation layers for the FastAPI/MongoDB backend.

### Technical Stack
- **Web:** Next.js 16.2.0 (App Router), Tailwind CSS v4, Zustand 5, SWR 2.3.
- **Mobile:** Expo 54, React Native 0.81.5.
- **Parity:** Shared TypeScript types from the monorepo workspace MUST dictate all UI data structures.

---

# 2. State & Context Sovereignty

### 2.1 Mandatory Project Lock
- **Project Selection:** After login, users must select a Project context via the `ProjectSelectorModal`.
- **Global Store:** The Active Project ID is stored in Zustand (`projectStore.ts`) and persisted in `localStorage`.
- **Hard Swap:** Switching a project MUST trigger a full page reload (`window.location.reload()`) and a total SWR cache purge (`mutate(() => true, undefined)`) to prevent cross-project data contamination.

### 2.2 Global State Layers
1. **Auth & JWT:** Handled via `authStore.ts`. Supports 401 token refresh cycles.
2. **Project Context:** Injected into every API request header via `X-Project-Id`.
3. **Data Strategy:** Zustand for client-side persistence; SWR for server-side state.

---

# 3. Design System: Luxury RuixenUI Aesthetic

The system has moved from generic Fintech to a high-fidelity, interactive "Luxury" aesthetic.

### 3.1 Visual Foundations
- **Primary Palette:** Zinc/Slate palette (Dark mode default).
- **Sidebar:** Zinc-950 (`#09090b`) with 1px borders and translucent hover states.
- **Backgrounds:** "High Density Grid" using a radial dot gradient on `white` or `zinc-950`.
- **Glassmorphism:** Intensive use of `backdrop-blur-3xl` and `bg-white/[0.03]` for panels.

### 3.2 Navigation & Feedback
- **Accent Color:** Orange-500 (`#f97316`) for active tabs, primary CTAs, and iconography.
- **Selection:** Indigo-based highlight contrasts.
- **Feedback:** `Sonner` toasts for success/error; custom `ErrorBoundary` for runtime failures.

---

# 4. Web CRM: Financial Grid Mastery

All financial data entry must utilize the `FinancialGrid.tsx` wrapper (AG Grid Community v33).

### 4.1 Grid Implementation Rules
- **Theme:** `ag-theme-quartz-dark` with minimalist typography and 24px horizontal padding.
- **Keyboard UX:** 
  - `Enter` key: Stops current editing and automatically moves focus to the same column in the row below.
  - `Tab` key: Native cell-to-cell navigation.
- **Formatting:** Right-aligned numeric fields with Indian Currency (`formatINR`) rounded to 2 decimals.
- **Validation:** Visual row-level markers (`border-left: 4px solid #ef4444` for invalid rows). Save actions are blocked if invalid rows exist.

---

# 5. Site Operations & Field Verification

### 5.1 Dashboard Tab Architecture
1. **DPR Review:** Gallery interface for site photos and delta notes with integrated Approval workflow.
2. **Attendance Verification:**
   - **GPS Verification:** All entries must display Google Maps links with latitude/longitude.
   - **Selfie Verification:** Workers must provide a check-in selfie viewable via an admin lightbox.
   - **Admin Audit:** Explicit "Verify Now" button to transition attendance logs to a verified state.
3. **Voice Logs:** Specialized audio player paired with transcribed text blocks.

---

# 6. Admin Mobile UX: Site Funds (V3 Rules)

The Mobile App provides a unified 'Site Funds' interface for Petty Cash and Site Overheads.

### 6.1 Logic Constraints
- **Zero Client Math:** Balances and totals are computed exclusively server-side to prevent arithmetic drift.
- **Security Constraint:** Mobile staff are restricted to **DEBIT only** entries. Category selection is auto-bound to the active fund type.
- **Transaction Integrity:** Idempotency keys (`tx-{timestamp}`) must be sent with all transactions to prevent double-entries during network instability.

### 6.2 Status Indicators
- **Deficit (Red):** Balance < 0.
- **Strict Limit (Amber):** Balance ≤ Threshold.

---

# 7. Error Handling & Multi-Session Logic

### 7.1 Concurrency & Conflicts
- **Version Conflict Modal:** Triggered when the backend identifies a version mismatch on editable entities (WO/PC/Budget).
- **Network Resilience:** `NetworkErrorRetry` component with automated backoff for failed SWR fetches.

---

# 8. Accessibility & Formatting Truths

- **Alignment:** All currency and numeric fields strictly right-aligned.
- **Symbols:** ₹ symbol mandatory for all localized financial displays.
- **Truth Source:** No auto-rounding on the frontend. UI must reflect the exact value received from the backend `Decimal128` fields.

---

# Conclusion

Frontend v3.0 is a **deterministic, luxury-tier financial interface** that mirrors Excel's precision while providing modern field verification tools (GPS/Selfies). It enforces strict transactional integrity via server-authoritative logic and mandatory project contexts.

---

**End of Enterprise Frontend Engineering Specification — Version 3.0 (Precision Release)**