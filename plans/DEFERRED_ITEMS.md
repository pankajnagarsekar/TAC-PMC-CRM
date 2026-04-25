# Deferred Features & Known Gaps (TAC-PMC CRM)

The following items were identified during the Phase 7 Reliability Hardening as deferred due to missing prerequisites, out-of-scope business logic, or required infrastructure configurations.

## 1. Daily Progress Report (DPR) Injection (BR5-053)
- **Issue:** No "Add DPR" button in the Site Operations module.
- **Status:** DEFERRED.
- **Reason:** Requires a specialized implementation of the DPR aggregate root which was not part of the current hardening phase. The backend supports DPR creation, but the specialized UI for injection needs to be designed.

## 2. OCR Post-Extraction Actions (BR5-056)
- **Issue:** No actionable buttons after OCR extraction (e.g., "Confirm & Save").
- **Status:** DEFERRED.
- **Reason:** The OCR module is currently in a "Read-Only" preview state. Actionable mapping of OCR fields to financial entities requires complex mapping logic and user verification steps.

## 3. Granular Screen Permissions (BR5-062)
- **Issue:** Only 5/13 screens have explicit permission gating implemented.
- **Status:** DEFERRED.
- **Reason:** Global "Admin-only" gates are active on critical financial creation paths. Full RBAC (Role Based Access Control) rollout across all minor screens is scheduled for the next architectural phase.

## 4. Live Site Feed (BR5-065 / BR6-006)
- **Issue:** The live site feed (activity stream) appears empty or placeholders.
- **Status:** DEFERRED.
- **Reason:** Requires the Audit Trail events to be streamed to a specialized activity collection. Integration with the frontend WebSocket or polling mechanism is pending.

## 5. AI Summary Synthesis (BR6-007)
- **Issue:** AI summary generation fails or shows errors.
- **Status:** DEFERRED.
- **Reason:** Requires a valid `GOOGLE_API_KEY` with Gemini access configured in the environment. The logic is implemented and hardened, but remains inactive without a key.

## 6. Real-time Collaboration (Architectural)
- **Issue:** Concurrent edits in the Scheduler can lead to stale state.
- **Status:** PARTIALLY ADDRESSED.
- **Reason:** Implemented Request Locking for financial saves. Real-time operational CRDTs or operational transforms for the Scheduler are out of scope for Phase 7.

---
**Zero Error Compliance State:** Verified. All active screens and flows pass build, lint, and core logic verification.
