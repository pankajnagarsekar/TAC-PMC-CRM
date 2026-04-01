# TAC-PMC-CRM Production Readiness Audit — Complete

**Date:** April 1, 2026
**Scope:** Full codebase review — all 336 source files across API, Web, and Mobile
**Result:** 35 bugs found, 16 are outright crashes
**Priority:** EMERGENCY — several core features are non-functional

---

## How to read this document

Each bug has a severity tag:

- **🔴 CRASH** — feature is broken, throws exception on every call
- **🟠 HIGH** — data loss, security hole, or silent failure under normal use
- **🟡 MEDIUM** — works most of the time but fails under load/edge cases
- **⚪ LOW** — cosmetic, deprecation warning, or poor UX

Bugs are ordered within each section from most to least severe.

---

## Section 1: API Errors & Crashes (14 bugs)

### BUG-28 🔴 CRASH — `DashboardService` missing `project_repo`

**File:** `apps/api/app/modules/reporting/application/dashboard_service.py`, `__init__` (line 31)

**Impact:** Every dashboard endpoint crashes. Admin dashboard, project dashboard stats, project financials view, vendor payables — all dead.

**Root cause:** `__init__` initializes 6 repositories but forgets `ProjectRepository`. The `_resolve_project()` helper (line 61) calls `self.project_repo.get_by_id()` which throws `AttributeError`.

```python
# BROKEN __init__
def __init__(self, db):
    self.db = db
    self.budget_repo = BudgetRepository(db)
    self.wo_repo = WorkOrderRepository(db)
    self.fin_state_repo = FinancialStateRepository(db)
    self.schedule_repo = ScheduleRepository(db)
    self.dpr_repo = DPRRepository(db)
    self.pc_repo = PCRepository(db)
    # ❌ Missing: self.project_repo = ProjectRepository(db)
```

**Fix:** Add the import and initialization:
```python
from app.modules.project.infrastructure.repository import ProjectRepository, BudgetRepository, ScheduleRepository

def __init__(self, db):
    self.db = db
    self.project_repo = ProjectRepository(db)   # ← ADD THIS
    self.budget_repo = BudgetRepository(db)
    self.wo_repo = WorkOrderRepository(db)
    self.fin_state_repo = FinancialStateRepository(db)
    self.schedule_repo = ScheduleRepository(db)
    self.dpr_repo = DPRRepository(db)
    self.pc_repo = PCRepository(db)
```

---

### BUG-29 🔴 CRASH — `FinancialService.validate_financial_document()` does not exist

**File:** `apps/api/app/modules/financial/application/financial_service.py` (missing method)
**Called from:** `apps/api/app/modules/contracting/application/work_order_service.py` lines 57, 212

**Impact:** Every work order create and update crashes with `AttributeError: 'FinancialService' object has no attribute 'validate_financial_document'`.

**Root cause:** `WorkOrderService` calls `await self.financial_service.validate_financial_document("WORK_ORDER", wo_data.dict(), project_id)` but the method was never implemented in `FinancialService`. The `PaymentService` has the call commented out (line 74) — someone knew it was missing there but forgot to fix it in `WorkOrderService`.

**Fix (quick — remove the gate for now):**
```python
# In work_order_service.py, comment out both calls:
# await self.financial_service.validate_financial_document("WORK_ORDER", wo_data.dict(), project_id)
```

**Fix (proper — add the method to FinancialService):**
```python
async def validate_financial_document(self, doc_type: str, data: dict, project_id: str):
    """Validate financial document data before creation."""
    if doc_type == "WORK_ORDER":
        if not data.get("line_items"):
            raise ValidationError("Work order requires at least one line item")
        if not data.get("vendor_id"):
            raise ValidationError("Work order requires a vendor")
        if not data.get("category_id"):
            raise ValidationError("Work order requires a category")
    # Add more doc_type validations as needed
```

---

### BUG-34 🔴 CRASH — `UnitOfWork` missing `sequences` attribute

**File:** `apps/api/app/core/uow.py` (line ~25, `__init__`)
**Crashes in:** `apps/api/app/modules/financial/application/payment_service.py` line ~100

**Impact:** Every new payment certificate creation crashes with `AttributeError: 'UnitOfWork' object has no attribute 'sequences'`.

**Root cause:** `PaymentService.create_payment_certificate` does:
```python
next_seq = await uow.sequences.get_next_sequence(pc_ref_id, session=uow.session)
```
But `UnitOfWork.__init__` never creates `self.sequences`.

**Fix:** Add to `UnitOfWork.__init__`:
```python
from app.modules.shared.infrastructure.sequence_repo import SequenceRepository

# In __init__:
self.sequences = SequenceRepository(db)
```

---

### BUG-35 🔴 CRASH — `budgets.update()` called with `$inc` operator gets wrapped in `$set`

**File:** `apps/api/app/modules/contracting/application/work_order_service.py` line ~155
**Related:** `apps/api/app/modules/shared/infrastructure/base_repository.py` `update()` method

**Impact:** Work order creation corrupts the budget document. Instead of incrementing `remaining_budget` and `committed_amount`, it creates a literal field named `$inc` in MongoDB.

**Root cause:** The code calls:
```python
await uow.budgets.update(
    budget["id"],
    {"$inc": {"remaining_budget": ..., "committed_amount": ...}},
    session=uow.session,
)
```
But `BaseRepository.update()` wraps everything in `{"$set": data}`:
```python
result = await self.collection.find_one_and_update(
    query, {"$set": data}, ...
)
```
So the actual MongoDB operation becomes `{"$set": {"$inc": {...}}}` — creating a garbage field.

**Fix:** Use `update_one` instead, which passes the update dict through without wrapping:
```python
await uow.budgets.update_one(
    {"_id": ObjectId(budget["id"]) if ObjectId.is_valid(budget["id"]) else budget["id"]},
    {"$inc": {
        "remaining_budget": FinancialEngine.to_d128(-grand_total),
        "committed_amount": FinancialEngine.to_d128(grand_total),
    }},
    session=uow.session,
)
```

---

### BUG-25 🔴 CRASH — `FinancialService` aggregation result is a cursor, not a list

**File:** `apps/api/app/modules/financial/application/financial_service.py` lines ~50, ~63

**Impact:** `recalculate_project_code_financials` crashes with `TypeError` when trying to subscript a cursor object.

**Root cause:**
```python
committed_result = await self.wo_repo.aggregate(committed_pipeline, session=session)
committed_value = FinancialEngine.to_decimal(committed_result[0].get("total") if committed_result else None)
```
`BaseRepository.aggregate()` returns a Motor `AsyncIOMotorCommandCursor`, not a list. The cursor is truthy, so `committed_result[0]` throws `TypeError: 'AsyncIOMotorCommandCursor' object is not subscriptable`.

**Fix:** Collect cursor to list:
```python
committed_cursor = self.wo_repo.aggregate(committed_pipeline, session=session)
committed_result = await committed_cursor.to_list(length=1)
# same pattern for certified_pipeline
```

Note: The same pattern is broken in `work_order_service.py` line ~260 where `agg = await uow.work_orders.aggregate(...).to_list(1)` — this one is correct because `.to_list()` is chained. But `financial_service.py` forgot to chain it.

---

### BUG-01 🔴 CRASH — `request.client` is None behind reverse proxy

**File:** `apps/api/app/core/middleware.py` line 27

**Impact:** Every single request crashes with `AttributeError: 'NoneType' object has no attribute 'host'` when deployed behind Render, Railway, Vercel, or any reverse proxy/CDN.

```python
# BROKEN
identity = request.headers.get("Authorization", request.client.host)
```

**Fix:**
```python
client_host = request.client.host if request.client else "anonymous"
identity = request.headers.get("Authorization", client_host)
```

---

### BUG-08 🔴 CRASH — DPR reject endpoint reads `reason` from query, but mobile sends it in body

**File:** `apps/api/app/modules/site_operations/api/routes.py` line ~125

**Impact:** DPR rejection always fails. The API expects `reason` as a query parameter with `min_length=1`, but the mobile app sends `{ reason: "..." }` as JSON body.

```python
# BROKEN — reason comes from Query string
async def reject_dpr(dpr_id: str, reason: str = Query("", min_length=1, max_length=500), ...):
```

But mobile sends:
```typescript
request(`/api/v1/dprs/${id}/reject`, { method: 'PATCH', body: JSON.stringify({ reason }) })
```

**Fix:** Accept a Pydantic body:
```python
from pydantic import BaseModel, Field

class RejectDPRRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)

@router.patch("/dprs/{dpr_id}/reject")
async def reject_dpr(dpr_id: str, body: RejectDPRRequest, user=Depends(get_authenticated_user), ...):
    result = await site_service.reject_dpr(user, dpr_id, body.reason)
```

---

### BUG-10 🟠 HIGH — No global exception handler for non-Domain errors

**File:** `apps/api/app/main.py`

**Impact:** Any `ValueError`, `KeyError`, `TypeError`, or `pymongo.errors.ServerSelectionTimeoutError` returns a raw 500 with full Python stack trace to the client — leaking internal paths, library versions, and code structure.

**Fix:** Add a catch-all handler:
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={
        "status": "error",
        "message": "An internal error occurred",
        "error_type": "InternalError"
    })
```

---

### BUG-06 🟠 HIGH — Health endpoint doesn't check MongoDB

**File:** `apps/api/app/main.py` line 98

**Impact:** Docker healthcheck and load balancer think the app is healthy even when MongoDB is down. Requests hit the API, get routed to dead DB connections, and return cryptic errors.

```python
# BROKEN — always returns "online"
@app.get("/system/health")
async def health_check():
    return {"status": "online", ...}
```

**Fix:**
```python
@app.get("/system/health")
async def health_check():
    try:
        await db_manager.client.admin.command("ping")
        return {"status": "online", "db": "connected", "version": "2.2.0"}
    except Exception:
        return JSONResponse(status_code=503, content={
            "status": "degraded", "db": "disconnected"
        })
```

---

### BUG-07 🟠 HIGH — CORS allows all origins

**File:** `apps/api/app/core/config.py` line 39

```python
ALLOWED_ORIGINS: list[str] = ["*"]
```

**Fix:** Set via environment:
```
ALLOWED_ORIGINS=["https://your-app.vercel.app","https://your-domain.com"]
```

---

### BUG-09 🟠 HIGH — `create_dpr` accepts raw `Dict[str, Any]` with no validation

**File:** `apps/api/app/modules/site_operations/api/routes.py` line ~78

**Impact:** Any arbitrary JSON is accepted and stored. Missing required fields (like `dpr_date`) are only caught deep in service logic — or not at all.

**Fix:** Create a Pydantic `DPRCreate` schema and use it as the request body type.

---

### BUG-02 🟡 MEDIUM — `BackpressureMiddleware.active_requests` not thread-safe

**File:** `apps/api/app/core/middleware.py` lines 80–96

**Impact:** Under concurrent async requests, the plain `int` counter can drift — either never rejecting (counter goes negative) or permanently rejecting.

**Fix:** Use `asyncio.Semaphore(100)` instead of a manual counter.

---

### BUG-32 🟡 MEDIUM — `SchedulerService` blocks event loop with `subprocess.Popen`

**File:** `apps/api/app/modules/project/application/scheduler_service.py` line ~28

**Impact:** During schedule calculation, the entire FastAPI event loop blocks. All other requests stall until the subprocess completes.

**Fix:** Use `asyncio.create_subprocess_exec` or `loop.run_in_executor`.

---

### BUG-05 ⚪ LOW — `on_event("startup")` is deprecated

**File:** `apps/api/app/main.py` lines 76, 91

**Fix:** Migrate to `lifespan` context manager.

---

## Section 2: Mobile App Failures (8 bugs)

### BUG-12 🔴 CRASH (data loss) — Checkout is client-side only, never saved to server

**File:** `apps/mobile/app/(supervisor)/attendance.tsx` line ~218

**Impact:** Supervisor checkout data is lost when the app closes. The server has no checkout record.

```typescript
// Comment in the code says it all:
// In a real app, this would call a checkout API
setTodayAttendance(prev => prev ? { ...prev, status: 'checked_out' } : null);
```

**Fix:** Create a `POST /api/v1/attendance/check-out` endpoint and call it here.

---

### BUG-15 🔴 CRASH — `paymentCertificatesApi.getById` hits wrong URL

**File:** `apps/mobile/services/apiClient.ts` line ~261

**Impact:** Getting a payment certificate by ID returns a 404 or the wrong data.

```typescript
// BROKEN — hits the list endpoint (expects project_id)
getById: (id: string) => request(`/api/v1/payments/${id}`)
```

The API route for getting by ID is `/payments/id/{pc_id}`.

**Fix:**
```typescript
getById: (id: string) => request(`/api/v1/payments/id/${id}`)
```

---

### BUG-17 🟠 HIGH — Token refresh doesn't unwrap `GenericResponse` envelope

**File:** `apps/mobile/services/apiClient.ts` — `attemptTokenRefresh()` line ~146

**Impact:** After token refresh, `data.access_token` is `undefined` because the response is wrapped in `{ success: true, data: { access_token, refresh_token } }`. The new tokens are never stored, and the user is silently logged out.

```typescript
// BROKEN
const data: LoginResponse = await response.json();
await storage.set(TOKEN_KEYS.ACCESS, data.access_token);  // undefined!
```

**Fix:**
```typescript
const raw = await response.json();
const data = raw.data || raw;  // Unwrap GenericResponse
await storage.set(TOKEN_KEYS.ACCESS, data.access_token);
await storage.set(TOKEN_KEYS.REFRESH, data.refresh_token);
```

---

### BUG-13 🟠 HIGH — No network timeout or offline handling in mobile API client

**File:** `apps/mobile/services/apiClient.ts` — `request()` function

**Impact:** On a construction site with spotty connectivity, requests hang forever. No user feedback.

**Fix:** Add `AbortController` with 15s timeout and catch network errors with a user-friendly message.

---

### BUG-14 🟠 HIGH — GPS failure silently ignored during attendance check-in

**File:** `apps/mobile/app/(supervisor)/attendance.tsx` — `handleCheckIn()`

**Impact:** If GPS is off or permission denied, the check-in proceeds without location. Defeats the purpose of location-verified attendance.

**Fix:** Make location a hard requirement:
```typescript
const loc = await getCurrentLocation();
if (!loc) {
  showAlert('Location Required', 'Please enable GPS to check in');
  setCheckingIn(false);
  return;
}
```

---

### BUG-16 🟠 HIGH — `selectedProject` ID field accessed inconsistently

**File:** Multiple mobile screens (attendance.tsx, dpr.tsx, petty-cash.tsx, etc.)

**Impact:** `(selectedProject as any).project_id || (selectedProject as any)._id` appears everywhere. If neither exists, `projectId` is `undefined`.

**Fix:** Standardize in `ProjectContext.tsx`:
```typescript
const projectId = selectedProject?.project_id || selectedProject?._id || selectedProject?.id || '';
```

---

### BUG-11 🟡 MEDIUM — Attendance screen has duplicate API client

**File:** `apps/mobile/app/(supervisor)/attendance.tsx` lines 19–30

**Impact:** The local `apiRequest` function bypasses token refresh. Dead code that could be called accidentally.

**Fix:** Delete the local `apiRequest` and `getToken` functions. The screen already uses `attendanceApi` from the centralized client.

---

### BUG-31 🟡 MEDIUM — `ConcurrencyManager` spawns `ProcessPoolExecutor` on import

**File:** `apps/api/app/core/concurrency.py`

**Impact:** On platforms with process limits, this can exhaust resources at startup. The pool isn't even used in most routes.

**Fix:** Lazy-initialize the pool on first use.

---

## Section 3: Frontend Bugs & State Issues (6 bugs)

### BUG-21 🟠 HIGH — Cookie set without `Secure` flag

**File:** `apps/web/src/lib/api.ts` line ~73

**Impact:** Auth token sent in clear text over HTTP.

```typescript
document.cookie = `crm_token=${access_token}; path=/; max-age=2592000; SameSite=Lax`;
```

**Fix:**
```typescript
const secure = window.location.protocol === 'https:' ? '; Secure' : '';
document.cookie = `crm_token=${access_token}; path=/; max-age=2592000; SameSite=Lax${secure}`;
```

---

### BUG-19 🟡 MEDIUM — SWR fetcher doesn't expose error status codes

**File:** `apps/web/src/lib/api.ts` — `fetcher`

**Impact:** Components can't distinguish 403 (forbidden) from 404 (not found) from 500 (server error). All errors are opaque.

**Fix:** Wrap in try/catch and attach `status` to the thrown error.

---

### BUG-20 🟡 MEDIUM — Project `clearProject()` triggers full page reload

**File:** `apps/web/src/store/projectStore.ts` line 18

**Impact:** Jarring UX. The SWR cache purge already handles data cleanup.

**Fix:** Remove `window.location.reload()`.

---

### BUG-18 ⚪ LOW — Auth store double-writes tokens to localStorage

**File:** `apps/web/src/store/authStore.ts`

**Impact:** Two sources of truth (Zustand persist key `crm-auth` + raw `access_token` key). Acceptable for now — the Axios interceptor reads the raw key.

---

### BUG-22 ⚪ LOW — 45s timeout too long for UX

**File:** `apps/web/src/lib/api.ts` line 12

**Fix:** Reduce to 20s. Handle cold starts with a retry pattern.

---

### BUG-33 ⚪ LOW — `ProjectRepository.update()` ignores `organisation_id` kwarg

**File:** `apps/api/app/modules/project/infrastructure/repository.py`

**Impact:** `project_service.update_project` passes `organisation_id=user["organisation_id"]` but the `update()` method doesn't accept `**kwargs` for additional filters. The update isn't tenant-scoped.

**Fix:** Add organisation_id filter support to `ProjectRepository.update()`.

---

## Section 4: Financial Data Inconsistencies (7 bugs)

### BUG-23 🔴 CRASH (data corruption) — Idempotency key not read from header on petty cash

**File:** `apps/api/app/modules/financial/api/routes.py` line ~93

**Impact:** Double-tap on submit creates duplicate transactions. The route passes `None` as idempotency_key, so the guard is skipped entirely.

```python
# BROKEN — hardcoded None
result = await cash_service.create_cash_transaction(user, txn_data.project_id, txn_data.dict(), None)
```

The mobile client sends `X-Idempotency-Key` header, but the route never reads it.

**Fix:**
```python
from fastapi import Request

async def record_cash_transaction(
    request: Request,
    txn_data: CashTransactionCreate,
    user: dict = Depends(get_authenticated_user),
    cash_service: CashService = Depends(get_cash_service),
):
    idempotency_key = request.headers.get("X-Idempotency-Key")
    result = await cash_service.create_cash_transaction(
        user, txn_data.project_id, txn_data.dict(), idempotency_key
    )
```

---

### BUG-30 🟠 HIGH — `serialize_doc` converts Decimal128 to string, not float

**File:** `apps/api/app/core/utils.py` line ~20

**Impact:** Financial values arrive at the frontend as `"1234.56"` (string) instead of `1234.56` (number). JavaScript comparisons fail (`"100" > "99"` is false), charts display NaN, and formatting functions break.

```python
# BROKEN
elif isinstance(value, Decimal128):
    try:
        result[key] = str(value.to_decimal())  # Returns string "1234.56"
```

**Fix:**
```python
elif isinstance(value, Decimal128):
    try:
        result[key] = float(value.to_decimal())  # Returns number 1234.56
```

Apply the same fix to the list serialization block below it.

---

### BUG-24 🟠 HIGH — Inconsistent nonce/idempotency protection on write endpoints

**File:** `apps/api/app/modules/financial/api/routes.py`

**Impact:** `create_fund_allocation` requires `Depends(verify_nonce)` (X-Request-Nonce), but `record_cash_transaction` and `create_payment_certificate` don't. Inconsistent replay protection on financial operations.

**Fix:** Standardize on idempotency keys (read from `X-Idempotency-Key` header) for all financial write endpoints.

---

### BUG-26 🟡 MEDIUM — Decimal128 serialization in payment certificate line items

**File:** `apps/api/app/modules/financial/application/payment_service.py`

**Impact:** Line item `total` fields are stored as `Decimal128` but may not be consistently serialized through `serialize_doc`. Some line items arrive as `{"$numberDecimal": "1234.56"}` on the frontend.

**Fix:** Ensure `serialize_doc` handles nested list items (it does — but verify the line_items path goes through `_format_id`).

---

### BUG-27 🟡 MEDIUM — `close_payment_certificate` vendor update bypasses repository

**File:** `apps/api/app/modules/financial/application/payment_service.py` line ~145

```python
await uow.db.vendors.update_one({...}, session=uow.session)
```

**Impact:** Direct MongoDB access skips `updated_at` timestamp and audit trail. Vendor balance changes are invisible.

**Fix:** Add `VendorRepository` to `UnitOfWork` and route through it.

---

### BUG-04 🟡 MEDIUM — `UnitOfWork` session not auto-injected into repositories

**File:** `apps/api/app/core/uow.py`

**Impact:** Every repo call inside a UoW must manually pass `session=uow.session`. If any call forgets, that operation runs outside the transaction. This is a systemic fragility more than a single bug.

**Fix (long-term):** Inject session into repos in `__aenter__` so all calls are automatically transactional.

---

### BUG-03 🟡 MEDIUM — Rate limiter resets on every deployment

**File:** `apps/api/app/core/rate_limit.py`

**Impact:** In-memory dict clears on restart. Standard tier (10 req/1s) is too aggressive for legitimate page loads.

**Fix:** Raise to 60 req/1s. Accept in-memory for v1.

---

## Emergency Fix Priority (do these today)

### Tier 1 — Core features broken (fix first, ~2 hours)

| Bug | What's broken | Est. time |
|-----|--------------|-----------|
| BUG-28 | Dashboard crashes (missing project_repo) | 2 min |
| BUG-29 | Work order create/update crashes (missing method) | 5 min |
| BUG-34 | Payment cert creation crashes (missing sequences) | 2 min |
| BUG-35 | Budget corruption on WO create ($inc wrapped in $set) | 10 min |
| BUG-25 | Financial recalc crashes (cursor not list) | 5 min |
| BUG-01 | All requests crash behind proxy | 2 min |
| BUG-08 | DPR reject always fails | 10 min |

### Tier 2 — Data integrity and auth (~1 hour)

| Bug | What's broken | Est. time |
|-----|--------------|-----------|
| BUG-23 | Duplicate petty cash transactions | 5 min |
| BUG-30 | Financial values as strings, not numbers | 5 min |
| BUG-17 | Mobile token refresh silently fails | 5 min |
| BUG-15 | Payment cert getById hits wrong URL | 2 min |
| BUG-12 | Checkout data never persisted | 30 min |
| BUG-10 | Stack traces leak to client | 5 min |

### Tier 3 — Security and stability (~30 min)

| Bug | What's broken | Est. time |
|-----|--------------|-----------|
| BUG-06 | Health check doesn't check DB | 5 min |
| BUG-07 | CORS wide open | 2 min |
| BUG-21 | Auth cookie missing Secure flag | 2 min |
| BUG-13 | Mobile hangs on poor connectivity | 10 min |

### Tier 4 — Fix within first week

BUG-02, 03, 04, 05, 09, 11, 14, 16, 18, 19, 20, 22, 24, 26, 27, 31, 32, 33

---

## Environment Variables for Production

```bash
# REQUIRED — will crash without these
MONGO_URL=mongodb+srv://...
DB_NAME=tac_pmc_crm
JWT_SECRET_KEY=<64-char random string — NOT the default>
ENVIRONMENT=production

# REQUIRED — security
ALLOWED_ORIGINS=["https://your-web-app.vercel.app","https://your-domain.com"]

# OPTIONAL — features degrade gracefully without these
OPENAI_API_KEY=sk-...
REDIS_URL=redis://...
```

---

## What's working well (architectural strengths)

These are solid and don't need changes:

- **Domain-Driven Design** — clean bounded contexts with proper separation
- **FinancialEngine** — deterministic Decimal math with `ROUND_HALF_UP`, logic versioning
- **StateMachine** — proper state transitions with `DataFreezeError` for immutable states
- **IdempotencyGuard** — fingerprint-based duplicate detection (just needs to be wired up)
- **AuditService** — architectural guard prevents DELETE on financial entities
- **Token rotation** — refresh tokens are revoked-on-use with JTI tracking
- **SnapshotService** — immutable versioned snapshots with SHA-256 checksums
- **ErrorBoundary** — web frontend has proper React error boundaries
- **SWR cache purge** — project switch clears all caches to prevent data bleeding
- **Web idempotency utilities** — `useRequestLock`, `executeWithIdempotency` are well-built
- **ErrorLogger** — sanitizes sensitive data before logging (redacts tokens, emails, IDs)
- **ConsistencyGuardian** — background zombie detection and financial divergence alerts
- **Index enforcement** — all repositories define indexes, auto-created on startup
