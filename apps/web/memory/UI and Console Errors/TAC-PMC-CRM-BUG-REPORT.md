# TAC-PMC CRM — Comprehensive Bug Report

> **Total Issues Found: 54**
> **Critical (App-Breaking): 16 | Major (Feature-Breaking): 24 | Minor (UX/Logic): 14**

---

## CRITICAL BUGS (Application-Breaking)

---

### BUG #1 — Login Fails: Double-Unwrapping of API Response

**File:** `apps/web/src/app/login/page.tsx` (Line ~34)

**Problem:** The Axios response interceptor in `api.ts` already unwraps `GenericResponse` envelopes (strips the outer `{success, data}` and returns `response.data = inner_data`). But the login page does an additional `(res.data as any).data || res.data` — effectively trying to access `data.data`, which will either be `undefined` (causing the fallback to work by accident on some shapes) or break entirely when the backend response shape changes.

**Impact:** Login may fail silently or extract `undefined` for `access_token`, `refresh_token`, `user` — resulting in a blank/broken post-login state.

**Fix:**
```tsx
// BEFORE (broken):
const serverData = (res.data as any).data || res.data;
const { access_token, refresh_token, user } = serverData;

// AFTER (correct):
const { access_token, refresh_token, user } = res.data as any;
```

---

### BUG #2 — X-Project-Id Header: `project_id` Fallback is Unreachable

**File:** `apps/web/src/lib/api.ts` (Lines 40–56)

**Problem:** The request interceptor tries to inject `X-Project-Id`. The logic is:
1. If `state.activeProject._id` → set header
2. `else if (typeof window !== "undefined")` → URL fallback
3. `else if (state.activeProject.project_id)` → set header

Branch 3 is **dead code** — it's nested inside an `if (typeof window !== "undefined")` block that already passed, so the `else if (typeof window !== "undefined")` in branch 2 is always true when branch 1 is false. Branch 3 never executes.

Many projects use `project_id` (a string ID) rather than `_id` (MongoDB ObjectId). These projects will **never get the X-Project-Id header**, causing all project-scoped API calls to fail with 400/403 errors.

**Impact:** All project-scoped features (financials, work orders, payment certificates, petty cash, DPRs, scheduler) silently fail for projects that don't have `_id` set.

**Fix:**
```ts
// BEFORE (broken logic):
if (state?.activeProject?._id) { ... }
else if (typeof window !== "undefined") { /* URL fallback */ }
else if (state?.activeProject?.project_id) { ... }  // UNREACHABLE

// AFTER (correct — check project_id first as it's the canonical ID):
const projId = state?.activeProject?.project_id || state?.activeProject?._id;
if (projId) {
  config.headers["X-Project-Id"] = String(projId);
} else if (typeof window !== "undefined") {
  // URL fallback ...
}
```

---

### BUG #3 — Client Modal Sends Wrong Field Names to Backend

**File:** `apps/web/src/components/clients/ClientModal.tsx` (Line ~54)

**Problem:** The form state uses `{name, email, phone, address, gstin}` and sends `formData` directly to the API. But the backend `ClientCreate` type expects `{client_name, client_email, client_phone, client_address, gst_number}`. The API will either reject the payload with validation errors or silently create clients with empty fields.

**Impact:** Creating or editing clients fails completely — all client data is lost or rejected by backend.

**Fix:**
```tsx
// BEFORE (sends wrong keys):
await api.post('/api/v1/clients/', formData);

// AFTER (map to correct API field names):
await api.post('/api/v1/clients/', {
  client_name: formData.name,
  client_email: formData.email,
  client_phone: formData.phone,
  client_address: formData.address,
  gst_number: formData.gstin,
});
// Same mapping needed for the PUT call
```

---

### BUG #4 — Client Grid Displays Wrong Field Names

**File:** `apps/web/src/app/admin/clients/page.tsx` (Lines ~40, ~55, ~68)

**Problem:** Cell renderers access `params.data.name`, `params.data.email`, `params.data.phone`, `params.data.gstin` — none of these fields exist on the `Client` type. The correct fields are `client_name`, `client_email`, `client_phone`, `gst_number`.

**Impact:** Client list shows empty/undefined values in every cell despite data being present.

**Fix:**
```tsx
// BEFORE:
(params.data as any).name || (params.data as any).client_name
(params.data as any).email || (params.data as any).client_email
(params.data as any).phone || (params.data as any).client_phone
(params.data as any).gstin || (params.data as any).gst_number

// AFTER:
params.data?.client_name
params.data?.client_email
params.data?.client_phone
params.data?.gst_number
```

---

### BUG #5 — Work Order Create: Inconsistent Project ID in URL vs Payload

**File:** `apps/web/src/app/admin/work-orders/new/page.tsx` (Lines ~144–155)

**Problem:** The payload uses `activeProject.project_id || activeProject._id` but the POST URL uses `activeProject._id || activeProject.project_id` (reversed priority). If a project has both fields set with different values, the URL targets one project while the payload claims another — causing a 400 or silent data corruption.

**Impact:** Work order creation may fail or create the WO under the wrong project.

**Fix:**
```tsx
// Standardize to project_id first (canonical identifier):
const projectId = activeProject.project_id || activeProject._id;
// Use `projectId` in BOTH the URL and payload
const response = await api.post(`/api/v1/work-orders/${projectId}`, {
  ...formData,
  project_id: projectId,
  line_items: lineItems,
});
```

---

### BUG #6 — WO Detail Page: CGST/SGST Shows Percentage, Not Calculated Amount

**File:** `apps/web/src/app/admin/work-orders/[id]/page.tsx` (Lines ~210–220)

**Problem:** In read-only mode, the financial breakdown displays `wo.cgst` and `wo.sgst` directly. But the `WorkOrder` type stores these as **percentage values** (e.g., `9`), not calculated amounts. The display shows "CGST: ₹9.00" instead of the actual tax amount (e.g., "₹45,000.00").

**Impact:** Financial breakdown in WO detail is completely wrong — showing percentages as currency amounts, making the numbers meaningless.

**Fix:**
```tsx
// BEFORE (shows percentage as currency):
{formatCurrency(isEditing ? editFinancials.cgst : wo.cgst || 0)}

// AFTER (calculate the actual amount):
{formatCurrency(isEditing ? editFinancials.cgst : (wo.total_before_tax || 0) * ((wo.cgst || 0) / 100))}
// Same for SGST
```

---

### BUG #7 — WO Grid Line Items: `qty` and `rate` Not Editable in Create Page

**File:** `apps/web/src/app/admin/work-orders/new/page.tsx` (Lines ~88–100)

**Problem:** The column definitions for `qty` and `rate` are missing `editable: true`. Only `description` has it. This means users cannot actually enter quantity or rate values in the grid — the line items are effectively broken.

**Impact:** Users cannot create work orders because line item amounts stay at 0.

**Fix:**
```tsx
// Add editable: true to qty and rate columns:
{
  field: "qty",
  headerName: "Qty",
  flex: 1,
  editable: true,  // ADD THIS
  type: "numericColumn",
  valueParser: (p: any) => Number(p.newValue) || 0,
},
{
  field: "rate",
  headerName: "Rate (₹)",
  flex: 1,
  editable: true,  // ADD THIS
  type: "numericColumn",
  valueParser: (p: any) => Number(p.newValue) || 0,
  valueFormatter: (p: any) => formatCurrency(p.value),
},
```

---

### BUG #8 — useRequestLock: Stale Closure Causes Race Conditions

**File:** `apps/web/src/lib/requestLock.ts` (Lines ~25–50)

**Problem:** `executeWithLock` uses `isLocked` from a React state closure. Since `useCallback` captures the `isLocked` value at creation time, rapid clicks can bypass the lock check because the `isLocked` boolean hasn't re-rendered yet. This is a classic stale closure bug.

**Impact:** Double-submissions of financial operations (Work Orders, Payment Certificates) — potentially creating duplicate records and corrupting budgets.

**Fix:**
```tsx
// Use a ref instead of state for the lock check:
const isLockedRef = useRef(false);

const executeWithLock = useCallback(
  async <T>(fn: () => Promise<T>): Promise<T | null> => {
    if (isLockedRef.current) {
      console.warn(`[RequestLock] Operation "${operationId}" blocked.`);
      return null;
    }
    isLockedRef.current = true;
    setIsLocked(true); // for UI display
    try {
      return await fn();
    } finally {
      isLockedRef.current = false;
      setIsLocked(false);
    }
  },
  [operationId],
);
```

---

### BUG #9 — Payment Certificate List: Paginated Response May Crash

**File:** `apps/web/src/app/admin/payment-certificates/page.tsx` (Lines 40–50)

**Problem:** The `fetchPCs` function does `const res = await api.get<{items, next_cursor}>()` then accesses `res.data.items`. But the response interceptor already unwraps GenericResponse envelopes. If the backend wraps in `{success: true, data: {items: [...], next_cursor: ...}}`, after interceptor unwrap `res.data = {items, next_cursor}` — which works. BUT if the backend returns `{items: [...], next_cursor: ...}` WITHOUT an envelope, the interceptor won't unwrap (no `success` key), and `res.data` is the raw Axios response data. Either way works by luck but the code has no safety check and will crash with `Cannot read properties of undefined (reading 'items')` if the response shape changes.

**Impact:** Payment certificates page crashes on load if response shape doesn't match exactly.

**Fix:**
```tsx
// Add safe extraction:
const responseData = res.data as any;
const pcItems = responseData?.items || responseData || [];
const cursor = responseData?.next_cursor || null;
```

---

### BUG #10 — Expense Entry Modal: `fetchCategories` in useCallback Dependency Causes Infinite Loop

**File:** `apps/web/src/components/petty-cash/ExpenseEntryModal.tsx` (Lines ~80–110)

**Problem:** `fetchCategories` is declared with `useCallback` and depends on `formData.category_id`. Inside `fetchCategories`, it calls `setFormData` to auto-select the first category (changing `category_id`). This triggers a re-creation of `fetchCategories`, which is a dependency of the `useEffect` that calls it — creating an **infinite fetch loop**.

**Impact:** The expense modal triggers unlimited API calls, potentially causing rate limiting, UI freezes, and backend overload.

**Fix:**
```tsx
// Remove formData.category_id from the dependency array of fetchCategories:
const fetchCategories = useCallback(async () => {
  // ... fetch logic
  if (uniqueCategories.length > 0) {
    setFormData((prev) => {
      if (!prev.category_id) return { ...prev, category_id: uniqueCategories[0]._id };
      return prev; // Don't update if already set
    });
  }
}, [projectId]); // Remove formData.category_id
```

---

### BUG #11 — Sidebar: Project Financials Link Uses Wrong ID Priority

**File:** `apps/web/src/components/layout/Sidebar.tsx` (Line ~82)

**Problem:** The Project Financials nav link uses `activeProject._id || activeProject.project_id`. But the `/api/v1/projects/[id]` route and the project detail page expect `project_id` as the URL parameter. If `_id` and `project_id` differ, the link navigates to a non-existent route.

**Impact:** "Project Financials" sidebar link leads to a 404 or loads wrong project data.

**Fix:**
```tsx
// BEFORE:
href: `/admin/projects/${activeProject._id || activeProject.project_id}`,

// AFTER:
href: `/admin/projects/${activeProject.project_id || activeProject._id}`,
```

---

### BUG #12 — PC Create: Sends Payload to Wrong Endpoint

**File:** `apps/web/src/app/admin/payment-certificates/new/page.tsx` (Line ~130)

**Problem:** The save handler POSTs to `/api/v1/payments/` but the PC list page fetches from `/api/v1/payments/${projectId}` and the detail page fetches from `/api/v1/payments/id/${id}`. The create endpoint likely expects the project ID in the URL (e.g., `/api/v1/payments/${projectId}`) to match the pattern, but it's sending to the root `/api/v1/payments/` without the project context in the URL.

**Impact:** PC creation may fail with 404/405 if the backend expects a project-scoped route.

**Fix:**
```tsx
// BEFORE:
return await api.post(`/api/v1/payments/`, payload, ...);

// AFTER (verify with backend route structure):
const projectId = activeProject.project_id || activeProject._id;
return await api.post(`/api/v1/payments/${projectId}`, payload, ...);
```

---

### BUG #13 — PC Create: GST Hardcoded at 18% Instead of Using Project/Settings Values

**File:** `apps/web/src/app/admin/payment-certificates/new/page.tsx` (Lines ~85–90)

**Problem:** The GST calculation is hardcoded as `rawSub * 0.18` (18%), ignoring the project's `project_cgst_percentage` and `project_sgst_percentage` values and the global settings CGST/SGST percentages. If a project has different tax rates (e.g., 5% GST for government projects), the financial preview will show wrong amounts.

**Impact:** Financial calculations are wrong for any project not using 9% CGST + 9% SGST. The amounts shown to users won't match what the backend calculates.

**Fix:**
```tsx
// Fetch and use actual project/settings tax rates:
const cgstRate = activeProject?.project_cgst_percentage ?? 9;
const sgstRate = activeProject?.project_sgst_percentage ?? 9;
const gstTotal = rawSub * ((cgstRate + sgstRate) / 100);
```

---

### BUG #14 — WO Create: Idempotency Key Reuse Across Sessions

**File:** `apps/web/src/app/admin/work-orders/new/page.tsx` (Line ~70)

**Problem:** `idempotency.get("WO_CREATE")` uses `getOrCreateIdempotencyKey` which stores the key in `sessionStorage`. If the user navigates away and comes back to the create page, the same key is reused. If a previous WO was successfully created with this key, the backend may return the cached response (idempotency replay) instead of creating a new WO.

**Impact:** Users may think they created a new WO but actually get redirected to a previously created one.

**Fix:**
```tsx
// Always generate a fresh key on mount:
useEffect(() => {
  clearIdempotencyKey("WO_CREATE");
  setIdempotencyKey(generateIdempotencyKey());
}, []);
```

---

## MAJOR BUGS (Feature-Breaking)

---

### BUG #15 — WO Detail: Edit mode `handleCellValueChanged` doesn't update the grid display

**File:** `apps/web/src/app/admin/work-orders/[id]/page.tsx` (Lines ~75–88)

**Problem:** When editing line items, `handleCellValueChanged` recalculates `data.total = qty * rate` but only calls `setEditLineItems` with the new data. It does NOT call `event.api.applyTransaction({ update: [data] })`, so the grid's displayed "Total" column doesn't refresh until the user clicks elsewhere.

**Impact:** The grid shows stale total values while editing, confusing users about the financial impact.

**Fix:**
```tsx
const handleCellValueChanged = useCallback((event: any) => {
  const { data, colDef, api: gridApi } = event;
  if (colDef.field === "qty" || colDef.field === "rate") {
    data.total = (parseFloat(data.qty) || 0) * (parseFloat(data.rate) || 0);
    gridApi.applyTransaction({ update: [data] }); // ADD THIS
  }
  setEditLineItems((prevItems) =>
    prevItems.map((item) => item.sr_no === data.sr_no ? { ...data } : item)
  );
}, []);
```

---

### BUG #16 — Settings Page: `client_permissions` Missing `can_view_scheduler` Field

**File:** `apps/web/src/app/admin/settings/page.tsx` (Lines ~35–40)

**Problem:** The local `GlobalSettings` interface defines `client_permissions` with only 3 fields: `can_view_dpr`, `can_view_financials`, `can_view_reports`. But the shared type in `packages/types` and the Sidebar component also check `can_view_scheduler`. The settings page doesn't render or save this permission, meaning it can never be toggled.

**Impact:** The scheduler permission for client users cannot be managed through the settings UI.

**Fix:**
```tsx
client_permissions: {
  can_view_dpr: boolean;
  can_view_financials: boolean;
  can_view_reports: boolean;
  can_view_scheduler: boolean; // ADD THIS
};
// And update the default state to include it:
client_permissions: {
  can_view_dpr: true,
  can_view_financials: false,
  can_view_reports: true,
  can_view_scheduler: false, // ADD THIS
},
```

---

### BUG #17 — Vendors Page: Uses Manual Fetch Instead of SWR (Inconsistent Pattern)

**File:** `apps/web/src/app/admin/vendors/page.tsx`

**Problem:** While every other data page (clients, users, categories) uses SWR for fetching, the vendors page uses manual `useState` + `useEffect` + `api.get()`. This means vendor data doesn't benefit from SWR's caching, deduplication, or revalidation. More critically, the `fetchVendors` function has `toast` as a dependency in `useCallback`, which can cause re-fetching loops if the toast reference changes.

**Impact:** Vendors page may re-fetch unnecessarily and doesn't stay in sync with other components that mutate vendor data.

**Fix:**
```tsx
// Replace manual fetch with SWR to match project pattern:
const { data: vendorsData, mutate, isLoading } = useSWR<Vendor[]>(
  "/api/v1/vendors/",
  fetcher
);
const vendors = vendorsData || [];
```

---

### BUG #18 — Categories Page: Delete Error Not Displayed

**File:** `apps/web/src/app/admin/categories/page.tsx` (Lines ~160–170)

**Problem:** The `confirmDelete` function catches errors and sets `setError(...)`, but this `error` state is only rendered inside the **Create/Edit modal**, not the Delete dialog. The delete dialog has already closed by the time the error is set, so the user never sees the error.

**Impact:** Category deletion fails silently — user thinks it worked but the category still exists.

**Fix:**
```tsx
// Add toast notification for delete errors:
async function confirmDelete() {
  if (!deleteCode) return;
  try {
    await axios.delete(`/api/v1/settings/codes/${deleteCode._id}`);
    mutate();
    setDeleteCode(null);
    // ADD: toast({ title: "Success", description: "Category deleted" });
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } };
    // CHANGE: Use toast instead of setError
    toast({
      title: "Error",
      description: err.response?.data?.detail || "Failed to delete category",
      variant: "destructive",
    });
    setDeleteCode(null);
  }
}
```

---

### BUG #19 — Dashboard: `loadSchedule` Called Without Error Handling

**File:** `apps/web/src/app/admin/dashboard/page.tsx` (Lines ~47–50)

**Problem:** `schedulerApi.load(activeProject.project_id).then(loadSchedule)` has no `.catch()` handler. If the scheduler endpoint returns 404 (no schedule yet) or 500, the unhandled rejection will log errors and potentially cause React to re-render with an error state.

**Impact:** Dashboard crashes or logs errors for projects that don't have scheduler data yet.

**Fix:**
```tsx
React.useEffect(() => {
  if (activeProject?.project_id) {
    schedulerApi.load(activeProject.project_id)
      .then(loadSchedule)
      .catch(() => {}); // Silently ignore — no schedule data is valid
  }
}, [activeProject?.project_id, loadSchedule]);
```

---

### BUG #20 — Dashboard: Hardcoded External Image Will Fail Without Internet

**File:** `apps/web/src/app/admin/dashboard/page.tsx` (Line ~270)

**Problem:** The "LIVE SITE FEED" card uses an Unsplash URL (`https://images.unsplash.com/...`). In production environments without external internet access or when Unsplash is down, this will show a broken image. The `unoptimized` prop also bypasses Next.js image optimization.

**Impact:** Broken image display in production; unnecessary external dependency.

**Fix:**
```tsx
// Replace with a local placeholder or conditionally render:
// Option A: Use a local image
// Option B: Add error handling with a fallback
<NextImage
  src="/images/site-placeholder.jpg" // Local fallback
  alt="Site Feed"
  fill
  className="object-cover"
/>
```

---

### BUG #21 — Project Selector Modal: `window.location.reload()` Destroys App State

**File:** `apps/web/src/components/layout/ProjectSelectorModal.tsx` (Line ~35)

**Problem:** When selecting a project, the modal calls `window.location.reload()` which does a full page reload. This destroys all React state, forces re-authentication checks, and causes a jarring UX. The comment says "Force a full page reload to ensure absolute financial data isolation" — but SWR cache purging (already done in `setActiveProject`) achieves this without a reload.

**Impact:** Selecting a project causes a full page reload, losing scroll position, form state, and causing a flash of loading states.

**Fix:**
```tsx
function selectProject(project: Project) {
  setActiveProject(project); // This already purges SWR cache
  onClose();
  // Remove: window.location.reload();
}
```

---

### BUG #22 — CreateUserModal: HTML Entities in Toast Message

**File:** `apps/web/src/components/users/CreateUserModal.tsx` (Line ~87)

**Problem:** The success toast uses `&quot;` HTML entities: `description: \`User &quot;${formData.name}&quot; created successfully\``. Template literals don't render HTML entities — they'll display literally as `User &quot;John&quot; created`.

**Impact:** Toast messages display garbled text with `&quot;` instead of actual quotes.

**Fix:**
```tsx
// BEFORE:
description: `User &quot;${formData.name}&quot; created successfully`,

// AFTER:
description: `User "${formData.name}" created successfully`,
```

---

### BUG #23 — EditUserModal: Same HTML Entity Bug in Toast

**File:** `apps/web/src/components/users/EditUserModal.tsx` (Line ~72)

**Problem:** Same as BUG #22 — `&quot;` in template literal.

**Fix:** Same as BUG #22.

---

### BUG #24 — WO Create Page: `removeLineItem` Function Closure Reference in Column Defs

**File:** `apps/web/src/app/admin/work-orders/new/page.tsx` (Lines ~100–115)

**Problem:** The `columnDefs` are memoized with `useMemo(() => [...], [])` (empty deps), but the action column's cellRenderer references `removeLineItem` which captures `lineItems` via closure. Since the memo has no deps, the cellRenderer always references the initial `lineItems` state.

**Impact:** Deleting rows may reference stale row indices, causing the wrong row to be deleted.

**Fix:**
```tsx
// Add lineItems.length to the dependency array:
const columnDefs = useMemo(() => [...], [lineItems.length]);
// Or use event.node.rowIndex within the renderer instead of closure
```

---

### BUG #25 — PC Detail Page: `woResponse?.items` May Be Wrong After Interceptor Unwrap

**File:** `apps/web/src/app/admin/payment-certificates/[id]/page.tsx` (Line ~60)

**Problem:** `const workOrders: WorkOrder[] = woResponse?.items || [];` assumes the work orders response has an `items` property. But after the response interceptor unwraps GenericResponse, `woResponse` may already be the items array directly (if the backend wraps in GenericResponse), or it may be `{items: [...], next_cursor: ...}` (paginated). The code doesn't handle both shapes.

**Impact:** Linked work orders may not display on the PC detail page.

**Fix:**
```tsx
const workOrders: WorkOrder[] = Array.isArray(woResponse)
  ? woResponse
  : woResponse?.items || [];
```

---

### BUG #26 — PC New Page: Same `woResponse` Parsing Issue

**File:** `apps/web/src/app/admin/payment-certificates/new/page.tsx` (Line ~55)

**Problem:** Same as BUG #25. `woResponse?.items?.filter(...)` fails if `woResponse` is already an array.

**Fix:** Same pattern as BUG #25.

---

### BUG #27 — WO List Page: Same Paginated Response Parsing Issue

**File:** `apps/web/src/app/admin/work-orders/page.tsx` (Lines ~65–75)

**Problem:** `res.data.items` and `res.data.next_cursor` — after interceptor unwrap, the structure depends on whether the backend uses GenericResponse or returns raw. No safe fallback.

**Fix:**
```tsx
const data = res.data as any;
const items = data?.items || (Array.isArray(data) ? data : []);
const cursor = data?.next_cursor || null;
```

---

### BUG #28 — FundsTab: `data?.items` May Be Wrong Shape

**File:** `apps/web/src/components/site-operations/FundsTab.tsx` (Line ~20)

**Problem:** `const transactions = useMemo(() => data?.items || [], [data]);` — same interceptor unwrap issue. If `data` is already an array after unwrap, `data?.items` is `undefined`.

**Fix:**
```tsx
const transactions = useMemo(
  () => Array.isArray(data) ? data : data?.items || [],
  [data]
);
```

---

### BUG #29 — ExpenseEntryModal: Sends `image_url` as Blob URL (Unusable by Backend)

**File:** `apps/web/src/components/petty-cash/ExpenseEntryModal.tsx` (Line ~130)

**Problem:** When a file is uploaded, `previewUrl` is set via `URL.createObjectURL(file)` — a local blob URL like `blob:http://localhost:3000/abc-123`. This blob URL is sent as `image_url` in the API payload. The backend cannot access blob URLs — they're browser-local only.

**Impact:** Receipt images are never actually saved; the backend receives an unusable URL.

**Fix:**
```tsx
// Upload the file separately via multipart/form-data, OR
// Convert to base64:
const toBase64 = (file: File): Promise<string> =>
  new Promise((res, rej) => {
    const reader = new FileReader();
    reader.onload = () => res(reader.result as string);
    reader.onerror = rej;
    reader.readAsDataURL(file);
  });

// Then use the base64 string instead of previewUrl
```

---

### BUG #30 — Sidebar: `searchParams` Usage Without Suspense Boundary

**File:** `apps/web/src/components/layout/Sidebar.tsx` (Line ~20)

**Problem:** `useSearchParams()` in Next.js App Router requires a `Suspense` boundary. Without it, the entire page will throw during static generation or show a hydration error.

**Impact:** Potential hydration errors or build failures in production.

**Fix:**
```tsx
// Wrap the Sidebar usage in a Suspense boundary in the parent layout,
// or use usePathname() parsing instead of useSearchParams()
```

---

## MINOR BUGS (UX/Logic Issues)

---

### BUG #31 — Site Operations Page: Same `useSearchParams` Suspense Issue

**File:** `apps/web/src/app/admin/site-operations/page.tsx` (Line ~8)

**Problem:** `useSearchParams()` without Suspense boundary.

**Fix:** Wrap in `<Suspense>` or use URL pathname parsing.

---

### BUG #32 — Dashboard Layout: `localStorage.getItem` in `useEffect` Without SSR Guard

**File:** `apps/web/src/app/admin/dashboard/page.tsx` (Lines ~80–83)

**Problem:** `localStorage.getItem(...)` is called inside `useEffect` which is client-only, so this won't crash. However, the layout state defaults to `DEFAULT_LAYOUT` and only updates after first render, causing a layout flash.

**Fix:** Initialize from localStorage using a lazy initializer in `useState`.

---

### BUG #33 — FinancialGrid: `tabToNextCell` Returns `boolean` But AG Grid Expects `CellPosition | null`

**File:** `apps/web/src/components/ui/FinancialGrid.tsx` (Lines ~120–140)

**Problem:** The `tabToNextCell` function sometimes returns `true` (a boolean), but the AG Grid API expects `CellPosition | null`. This causes TypeScript errors and unpredictable tab navigation behavior.

**Fix:**
```tsx
// Return the next cell position or null, not boolean:
const tabToNextCell = useCallback(
  (params: TabToNextCellParams): CellPosition | null => {
    if (params.editing) params.api.stopEditing();
    return params.nextCellPosition || null;
  },
  [],
);
```

---

### BUG #34 — Settings Page: `retention_percentage` Not in Backend `GlobalSettings` Type

**File:** `apps/web/src/app/admin/settings/page.tsx` (Line ~26)

**Problem:** The local settings interface includes `retention_percentage` but the shared `GlobalSettings` type in `packages/types` doesn't have this field. It will be sent to the backend but may be silently ignored.

**Impact:** Retention percentage setting is displayed but never persists.

**Fix:** Add `retention_percentage` to the shared `GlobalSettings` type, or remove from settings UI if backend doesn't support it.

---

### BUG #35 — Sidebar: Child Menu Active Detection Fails for Base Path

**File:** `apps/web/src/components/layout/Sidebar.tsx` (Lines ~195–200)

**Problem:** `isActive` checks `pathname === item.href` for parent items. For `/admin/scheduler` (no query params), this matches. But if the user is on `/admin/scheduler?tab=gantt`, `pathname` is still `/admin/scheduler`, so the parent activates correctly. However, for `/admin/site-operations`, the child detection uses `pathname === childPath` where `childPath` is the href without query params — this always matches the parent, making ALL children appear active simultaneously.

**Impact:** All sub-menu items under Site Operations appear active at once.

**Fix:**
```tsx
// Fix child active detection to also check query params:
const currentTab = searchParams.get('tab');
const isSideChildActive = pathname === childPath &&
  (childTab ? currentTab === childTab : !currentTab);
```

---

### BUG #36 — Admin Layout: Client Role Gets `client-readonly` Class But No CSS Prevents Edits

**File:** `apps/web/src/app/admin/layout.tsx` (Line ~97)

**Problem:** The `client-readonly` class is conditionally applied to `<main>`, and there are `admin-only` classes on buttons throughout the app. However, there's no corresponding CSS that actually hides `admin-only` elements or prevents interaction in `client-readonly` mode. Client users can see all admin buttons.

**Impact:** Client users see (and can click) admin-only buttons like Create, Edit, Delete.

**Fix:** Add global CSS rules:
```css
.client-readonly .admin-only {
  display: none !important;
}
```

---

### BUG #37 — DPR Tab: `fetchDPRs` in useEffect Has `activeProject` AND `fetchDPRs` as Dependencies

**File:** `apps/web/src/components/site-operations/DPRTab.tsx` (Lines ~55–60)

**Problem:** The `useEffect` depends on `[activeProject, statusFilter, startDate, endDate, fetchDPRs]`. Since `fetchDPRs` is a `useCallback` that depends on `[activeProject, statusFilter, startDate, endDate]`, every change to any of these creates a new `fetchDPRs` reference, triggering the useEffect. The effect then calls `fetchDPRs()`, which is fine — but the dual dependency on both `activeProject` and `fetchDPRs` means the fetch runs twice on project change.

**Impact:** Double API calls on every filter/project change.

**Fix:**
```tsx
// Remove the individual values from useEffect, keep only fetchDPRs:
useEffect(() => {
  if (activeProject?.project_id) {
    fetchDPRs();
  }
}, [fetchDPRs]);
```

---

### BUG #38 — WO New Page: `removeLineItem` in Column Defs Uses `params.node.rowIndex` Instead of Grid API

**File:** `apps/web/src/app/admin/work-orders/new/page.tsx` (Line ~110)

**Problem:** The delete button calls `removeLineItem(params.node.rowIndex)` directly, bypassing the confirmation dialog. But `removeLineItem` sets `setDeleteRowIndex(index)` to show the dialog. If `params.node.rowIndex` is `0`, JavaScript treats it as falsy and the dialog condition `deleteRowIndex !== null` evaluates incorrectly (since `0 !== null` is true, this actually works). However, the dialog's cancel button sets `setDeleteRowIndex(null)`, and the minimum row check `lineItems.length === 1` can prevent deletion of the last row — but only inside `confirmDeleteRow`, not in the grid button itself.

**Impact:** Minor — the flow works but `rowIndex` of 0 could cause confusion in edge cases. The real issue is the stale closure from BUG #24.

**Fix:** Address as part of BUG #24 fix.

---

## Summary Table

| # | Severity | Area | File | One-Line Description |
|---|----------|------|------|---------------------|
| 1 | CRITICAL | Auth | login/page.tsx | Double-unwrapping kills login |
| 2 | CRITICAL | API | lib/api.ts | project_id fallback unreachable |
| 3 | CRITICAL | Clients | ClientModal.tsx | Wrong field names sent to API |
| 4 | CRITICAL | Clients | clients/page.tsx | Grid shows undefined values |
| 5 | CRITICAL | Work Orders | work-orders/new | URL vs payload project ID mismatch |
| 6 | CRITICAL | Work Orders | work-orders/[id] | CGST/SGST shows % not amount |
| 7 | CRITICAL | Work Orders | work-orders/new | qty/rate columns not editable |
| 8 | CRITICAL | Infra | requestLock.ts | Stale closure allows double-submit |
| 9 | CRITICAL | Payments | payment-certificates/page.tsx | Paginated response may crash |
| 10 | CRITICAL | Petty Cash | ExpenseEntryModal.tsx | Infinite fetch loop |
| 11 | CRITICAL | Nav | Sidebar.tsx | Project financials wrong link |
| 12 | CRITICAL | Payments | payment-certificates/new | POST to wrong endpoint |
| 13 | CRITICAL | Payments | payment-certificates/new | GST hardcoded at 18% |
| 14 | CRITICAL | Work Orders | work-orders/new | Idempotency key reuse |
| 15 | MAJOR | Work Orders | work-orders/[id] | Grid total doesn't refresh on edit |
| 16 | MAJOR | Settings | settings/page.tsx | Missing scheduler permission |
| 17 | MAJOR | Vendors | vendors/page.tsx | Manual fetch instead of SWR |
| 18 | MAJOR | Categories | categories/page.tsx | Delete error not shown |
| 19 | MAJOR | Dashboard | dashboard/page.tsx | Scheduler load no error handler |
| 20 | MAJOR | Dashboard | dashboard/page.tsx | External image dependency |
| 21 | MAJOR | Projects | ProjectSelectorModal.tsx | Full page reload on switch |
| 22 | MAJOR | Users | CreateUserModal.tsx | HTML entities in toast |
| 23 | MAJOR | Users | EditUserModal.tsx | HTML entities in toast |
| 24 | MAJOR | Work Orders | work-orders/new | Stale closure in column defs |
| 25 | MAJOR | Payments | payment-certificates/[id] | woResponse shape mismatch |
| 26 | MAJOR | Payments | payment-certificates/new | Same woResponse issue |
| 27 | MAJOR | Work Orders | work-orders/page.tsx | Paginated response parsing |
| 28 | MAJOR | Funds | FundsTab.tsx | data.items shape mismatch |
| 29 | MAJOR | Petty Cash | ExpenseEntryModal.tsx | Blob URL sent as image_url |
| 30 | MAJOR | Nav | Sidebar.tsx | useSearchParams needs Suspense |
| 31 | MINOR | Site Ops | site-operations/page.tsx | useSearchParams Suspense |
| 32 | MINOR | Dashboard | dashboard/page.tsx | Layout flash from localStorage |
| 33 | MINOR | Grid | FinancialGrid.tsx | tabToNextCell wrong return type |
| 34 | MINOR | Settings | settings/page.tsx | retention_percentage not in type |
| 35 | MINOR | Nav | Sidebar.tsx | All children appear active |
| 36 | MINOR | Auth | admin/layout.tsx | admin-only buttons visible to clients |
| 37 | MINOR | Site Ops | DPRTab.tsx | Double fetch on filter change |
| 38 | MINOR | Work Orders | work-orders/new | rowIndex edge case |
| 39 | CRITICAL | UI/Theme | globals.css | Undefined CSS variables break light mode |
| 40 | CRITICAL | UI/Theme | globals.css | `--sidebar-active` missing in light mode |
| 41 | MAJOR | UI/Theme | tailwind.config.ts | Color values aren't wrapped in `hsl()` |
| 42 | MAJOR | UI/Dialog | dialog.tsx | Dark-only hardcoded styles ignore light mode |
| 43 | MAJOR | UI/Theme | globals.css | `body` font-family mismatch vs layout.tsx |
| 44 | MAJOR | UI/Vendors | vendors/page.tsx | Hardcoded dark-mode styles ignore light mode |
| 45 | MAJOR | UI/ErrorBoundary | ErrorBoundary.tsx | Hardcoded white bg ignores dark mode |
| 46 | MAJOR | UI/VersionConflict | VersionConflictModal.tsx | Hardcoded slate-900 bg ignores light mode |
| 47 | MAJOR | UI/Network | NetworkErrorRetry.tsx | Hardcoded amber-50 bg ignores dark mode |
| 48 | MAJOR | UI/Login | login/page.tsx | Login page unusable in light mode |
| 49 | MINOR | UI/KPICard | KPICard.tsx | References undefined CSS variables |
| 50 | MINOR | UI/Button | button.tsx | Hardcoded gray/blue, ignores theme system |
| 51 | MINOR | UI/Breadcrumbs | breadcrumbs.tsx | Only styled for light; dark hover broken |
| 52 | MINOR | UI/ModeToggle | mode-toggle.tsx | Moon icon uses `absolute` without container |
| 53 | MINOR | UI/Dashboard | dashboard/page.tsx | Project search input dark-only styling |
| 54 | MINOR | UI/Grid | FinancialGrid.tsx | `<style jsx global>` leaks across routes |

---

## UI / THEME / VISUAL BUGS

---

### BUG #39 — CRITICAL: Multiple CSS Variables Referenced But Never Defined

**File:** `apps/web/src/app/globals.css` + `apps/web/tailwind.config.ts`

**Problem:** Several CSS variables are referenced in code but **never defined** in `:root` or `.dark`:

- `--luxury-orange` — used in `.btn-primary-luxury` and `.empty-state-luxury-icon` in globals.css, and in tailwind config as `luxury.orange`
- `--luxury-orange-hover` — used in `.btn-primary-luxury:hover`
- `--luxury-orange-shadow` — used in `.btn-primary-luxury` box-shadow
- `--kpi-positive-text`, `--kpi-positive-bg`, `--kpi-positive-shadow` — used in KPICard.tsx STATUS_CONFIG
- `--kpi-negative-text`, `--kpi-negative-bg`, `--kpi-negative-shadow` — same
- `--kpi-warning-text`, `--kpi-warning-bg`, `--kpi-warning-shadow` — same
- `--kpi-neutral-text`, `--kpi-neutral-bg`, `--kpi-neutral-shadow` — same
- `--destructive` / `--destructive-foreground` — defined only in `.dark`, missing from `:root` (light mode)

**Impact:** KPI cards render with invisible or transparent colors. The `.btn-primary-luxury` class produces invisible buttons. Empty states have invisible icons. Light mode has no destructive color defined. Everything depending on these variables is visually broken.

**Fix:** Add all missing variable definitions to both `:root` and `.dark`:
```css
:root {
  --luxury-orange: 24 95% 53%;
  --luxury-orange-hover: 24 95% 45%;
  --luxury-orange-shadow: rgba(249, 115, 22, 0.3);
  --destructive: 0 84.2% 60.2%;
  --destructive-foreground: 0 0% 98%;
  /* KPI status tokens */
  --kpi-positive-text: 142 71% 45%;
  --kpi-positive-bg: rgba(34, 197, 94, 0.1);
  --kpi-positive-shadow: rgba(34, 197, 94, 0.15);
  --kpi-negative-text: 0 84% 60%;
  --kpi-negative-bg: rgba(239, 68, 68, 0.1);
  --kpi-negative-shadow: rgba(239, 68, 68, 0.15);
  --kpi-warning-text: 38 92% 50%;
  --kpi-warning-bg: rgba(245, 158, 11, 0.1);
  --kpi-warning-shadow: rgba(245, 158, 11, 0.15);
  --kpi-neutral-text: 215 16% 47%;
  --kpi-neutral-bg: rgba(148, 163, 184, 0.1);
  --kpi-neutral-shadow: rgba(148, 163, 184, 0.15);
}
```

---

### BUG #40 — CRITICAL: `--sidebar-active` Not Defined in Light Mode

**File:** `apps/web/src/app/globals.css`

**Problem:** `--sidebar-active` and `--sidebar-active-foreground` are only defined inside `.dark { }`. In light mode, the Sidebar's active navigation items, the user avatar circle, and other elements using `bg-sidebar-active` / `text-sidebar-active-foreground` render as transparent/invisible.

**Impact:** In light mode, the active sidebar item has no background highlight, and the user avatar is invisible.

**Fix:**
```css
:root {
  --sidebar-active: 214 32% 91%;
  --sidebar-active-foreground: 38 66% 35%;
}
```

---

### BUG #41 — Tailwind Config Color Values Not Wrapped in `hsl()` Correctly

**File:** `apps/web/tailwind.config.ts`

**Problem:** Most non-sidebar colors use raw `var(--background)` without `hsl()` wrapping:
```ts
background: "var(--background)",  // This is "210 20% 98%" — not a valid CSS color
```
CSS variables store raw HSL values like `210 20% 98%`. Without `hsl()`, Tailwind classes like `bg-background` inject `background-color: var(--background)` which evaluates to `background-color: 210 20% 98%` — an invalid CSS value. Meanwhile, sidebar colors correctly use `hsl(var(--sidebar-background))`.

**Impact:** `bg-background`, `text-foreground`, `bg-primary`, `bg-card`, etc. all produce **invalid CSS colors**. The background may appear white/transparent only because browsers fall back to defaults, but opacity modifiers like `bg-primary/50` will completely fail.

**Fix:**
```ts
// Wrap ALL color values in hsl():
background: "hsl(var(--background))",
foreground: "hsl(var(--foreground))",
primary: {
  DEFAULT: "hsl(var(--primary))",
  foreground: "hsl(var(--primary-foreground))",
},
// ... same for all other non-sidebar colors
```

---

### BUG #42 — Dialog Component Hardcoded to Dark Theme

**File:** `packages/ui/src/components/dialog.tsx`

**Problem:** The `DialogContent` component has hardcoded dark-theme styles: `border-slate-800 bg-slate-950`. These are baked into the base component, not using theme variables. In light mode, dialogs appear as dark rectangles on a light background.

Additionally, every page that uses `<DialogContent>` also passes dark-only overrides like `className="bg-slate-950 border-slate-800 text-white"`, doubling down on the dark-only styling.

**Impact:** All dialogs (client CRUD, vendor CRUD, category CRUD, delete confirmations, version conflict, WO row delete) appear with dark backgrounds in light mode, clashing with the light theme.

**Fix:**
```tsx
// In dialog.tsx base component:
'border border-border bg-card text-card-foreground p-6 shadow-lg ...'

// In all consumer pages, remove hardcoded dark overrides:
// BEFORE: className="bg-slate-950 border-slate-800 text-white"
// AFTER:  className="" (let base theme handle it)
```

---

### BUG #43 — Body Font Mismatch: globals.css Says 'Manrope', layout.tsx Uses Inter

**File:** `apps/web/src/app/globals.css` (Line ~68) + `apps/web/src/app/layout.tsx` (Line ~5)

**Problem:** `globals.css` sets `body { font-family: 'Manrope', sans-serif; }` but `layout.tsx` loads the `Inter` font from Google and applies `className={inter.className}` to `<body>`. The `inter.className` generates a scoped CSS class that sets `font-family: '__Inter_...', sans-serif`. Since element styles (`inter.className`) have the same specificity as the CSS rule, the result depends on load order — it's **unpredictable** which font wins.

**Impact:** Font may flicker between Manrope and Inter on page loads. If Manrope isn't loaded (no @import for it), the CSS rule falls back to `sans-serif` while Inter works fine — but the declarations fight each other.

**Fix:** Either:
- Remove the `font-family` from `globals.css` and rely on `layout.tsx`'s Inter, OR
- Change `layout.tsx` to use Manrope and remove Inter

---

### BUG #44 — Vendors Page: All Styles Hardcoded to Dark Mode

**File:** `apps/web/src/app/admin/vendors/page.tsx`

**Problem:** Unlike the clients/categories pages which use `dark:` prefixed classes (e.g., `bg-white dark:bg-slate-900/50`), the vendors page exclusively uses dark-mode styles: `bg-slate-900/40`, `text-white`, `bg-slate-950/80`, `border-white/5`, `text-orange-500`. No light-mode alternatives are provided.

**Impact:** In light mode, the vendors page has dark backgrounds on a light page, unreadable text (white-on-white in some areas), and a completely broken visual appearance.

**Fix:** Add `dark:` prefixed variants matching the pattern used in clients/categories pages:
```tsx
// BEFORE:
"bg-slate-900/40 border border-white/5 rounded-[2.5rem]"

// AFTER:
"bg-white dark:bg-slate-900/40 border border-zinc-200 dark:border-white/5 rounded-[2.5rem]"
```

---

### BUG #45 — ErrorBoundary: Hardcoded White Background, No Dark Mode

**File:** `apps/web/src/components/ui/ErrorBoundary.tsx`

**Problem:** The error fallback UI uses hardcoded light-theme styles: `bg-white`, `border-red-100`, `text-gray-900`, `text-gray-600`, `bg-gray-50`. In dark mode, this renders as a jarring white box on a dark background.

**Impact:** Error states look broken in dark mode.

**Fix:** Use theme-aware classes:
```tsx
"bg-card border-destructive/20 text-card-foreground"
```

---

### BUG #46 — VersionConflictModal: Dark-Only Hardcoded Styles

**File:** `apps/web/src/components/ui/VersionConflictModal.tsx`

**Problem:** Uses `bg-slate-900`, `border-slate-800`, `text-slate-300` without light-mode alternatives.

**Impact:** In light mode, the modal appears as an unreadable dark box.

**Fix:** Use `bg-card border-border text-card-foreground` or add `dark:` prefixes.

---

### BUG #47 — NetworkErrorRetry: Light-Only Hardcoded Styles

**File:** `apps/web/src/components/ui/NetworkErrorRetry.tsx`

**Problem:** The opposite problem — uses `bg-amber-50`, `border-amber-200`, `text-amber-900` without dark-mode variants.

**Impact:** In dark mode, the network error banner appears as a jarring light yellow bar.

**Fix:** Add `dark:bg-amber-900/20 dark:border-amber-500/20 dark:text-amber-200` etc.

---

### BUG #48 — Login Page: Completely Unusable in Light Mode

**File:** `apps/web/src/app/login/page.tsx`

**Problem:** The entire login page is styled exclusively for dark mode: `text-white`, `text-slate-400`, `bg-zinc-950/50`, aurora glows with dark colors, `text-zinc-800` for placeholders. There are zero light-mode overrides anywhere. The `bg-mesh-ultra` class from globals.css uses transparent gradients, so the background is effectively the theme `--background` — which is light gray in light mode. White text on a light gray background is invisible.

**Impact:** Login page is **completely unreadable** in light mode. Users cannot see the form fields, labels, or branding.

**Fix:** Add comprehensive `dark:` prefixes or wrap the login page in `className="dark"` to force dark mode on this specific page:
```tsx
// Quick fix — force dark mode on login page:
<div className="min-h-screen flex bg-mesh-ultra font-sans dark">
```

---

### BUG #49 — KPICard: References Non-Existent CSS Variables for Status Colors

**File:** `apps/web/src/components/ui/KPICard.tsx` (Lines ~20–26)

**Problem:** `STATUS_CONFIG` references CSS variables like `hsl(var(--kpi-positive-text))`, `var(--kpi-positive-bg)`, `var(--kpi-positive-shadow)` — none of which are defined anywhere in the CSS. This is a sub-issue of BUG #39 but specifically affects the inline styles in KPICard which are used for the icon glow, background gradient, and shadow.

**Impact:** KPI card status indicators (positive/negative/warning) are all transparent/invisible. The colored glow, icon background, and shadow effects don't render.

**Fix:** Define the variables (see BUG #39) or switch to direct Tailwind classes:
```tsx
const STATUS_CONFIG = {
  positive: { accent: '#22c55e', bg: 'rgba(34,197,94,0.1)', text: '#22c55e', shadow: 'rgba(34,197,94,0.15)' },
  // ...
};
```

---

### BUG #50 — Button Component: Uses Hardcoded Gray/Blue, Ignores Theme

**File:** `apps/web/src/components/ui/button.tsx`

**Problem:** The button variants use raw Tailwind colors (`bg-blue-600`, `bg-gray-100`, `border-gray-300`) instead of theme variables (`bg-primary`, `bg-muted`, `border-border`). This means buttons don't adapt to the theme.

**Impact:** Buttons in the ErrorBoundary and potentially other shared components use blue/gray which clash with the orange/gold theme used everywhere else.

**Fix:**
```tsx
const variantStyles = {
  default: "bg-primary text-primary-foreground hover:bg-primary/90",
  destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  outline: "border border-border bg-card hover:bg-accent hover:text-accent-foreground",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  ghost: "hover:bg-accent hover:text-accent-foreground",
  link: "text-primary underline-offset-4 hover:underline",
};
```

---

### BUG #51 — Breadcrumbs: Link Hover Color Dark-Mode Broken

**File:** `apps/web/src/components/ui/breadcrumbs.tsx`

**Problem:** Breadcrumb links use `hover:text-zinc-900` which works in light mode but is invisible in dark mode (dark gray on dark background). The Home icon similarly only has `text-zinc-500` without a dark variant.

**Fix:**
```tsx
<Link href={item.href} className="hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors">
```

---

### BUG #52 — ModeToggle: Moon Icon Uses `absolute` Without Relative Container

**File:** `apps/web/src/components/ui/mode-toggle.tsx`

**Problem:** The Moon icon has `className="absolute ..."` but the parent `<button>` doesn't have `relative` positioning. The Moon icon is positioned relative to the nearest positioned ancestor (likely the header bar), not the button itself.

**Impact:** The Moon icon may appear displaced from the button, especially if the header layout changes.

**Fix:**
```tsx
<button className="relative inline-flex items-center justify-center ...">{/* ... */}</button>
```

---

### BUG #53 — Dashboard No-Project State: Search Input Dark-Only Styling

**File:** `apps/web/src/app/admin/dashboard/page.tsx` (Line ~200)

**Problem:** The project search input uses `bg-zinc-950/50`, `border-white/5`, `text-white` without light-mode alternatives. In light mode, you get a near-black input on a light background.

**Impact:** Project search is visually broken in light mode.

**Fix:**
```tsx
className="w-full bg-zinc-50 dark:bg-zinc-950/50 border border-zinc-200 dark:border-white/5 rounded-2xl pl-12 pr-4 py-4 text-zinc-900 dark:text-white outline-none ..."
```

---

### BUG #54 — FinancialGrid: `<style jsx global>` Leaks Styles Across Routes

**File:** `apps/web/src/components/ui/FinancialGrid.tsx` (Lines ~190–230)

**Problem:** The component uses `<style jsx global>` to inject AG Grid theme overrides. In Next.js, `jsx global` styles are supposed to be scoped to the component's lifecycle, but they actually persist across route changes because Next.js doesn't reliably clean them up in client-side navigation. Multiple FinancialGrid instances on different pages stack up duplicate style tags.

**Impact:** Style tags accumulate in the DOM during navigation, potentially causing performance degradation and style specificity conflicts.

**Fix:** Move AG Grid overrides to `globals.css` as permanent global styles (they're always the same), or use a CSS Module.
