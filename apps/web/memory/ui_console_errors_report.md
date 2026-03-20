# TAC-PMC-CRM — UI & Console Errors Report

## CONSOLE ERRORS

### CE-01 — AG Grid: No Modules Registered (Error #272)
**Status:** ✅ CONFIRMED  
**Affected:** Clients, Projects, Categories, Work Orders — all render blank table areas  

**Fix:**  
Add:
```ts
ModuleRegistry.registerModules([AllCommunityModule])
```
Once globally in `_app.tsx` or a shared AG Grid config wrapper.

---

### CE-02 — Next.js (15.1.0) Outdated
**Status:** ✅ CONFIRMED  

**Fix:**  
```bash
npm install next@latest
```

---

## 🔴 CRITICAL ROUTING ERRORS

### UR-01 — Session Expiry / Logout Loop (CRITICAL)
**Status:** ✅ CONFIRMED  

Session expires in under 5–10 seconds. Any direct URL navigation triggers immediate logout.

**Fix:**  
- Set:
```ts
maxAge: 30 * 24 * 60 * 60
```
- Add silent refresh token mechanism

---

### UR-02 — Site Overheads → 404 Not Found (CRITICAL)
**Status:** ✅ CONFIRMED  

**Fix:**  
Create:
```
app/admin/site-overheads/page.tsx
```

---

### UR-03 — Reports Page Not Navigating / Missing (CRITICAL)
**Status:** ✅ CONFIRMED  

**Fix:**  
Create:
```
app/admin/reports/page.tsx
```

---

### UR-04 — Dashboard Links Point to Undefined Project (CRITICAL)
**Status:** ✅ CONFIRMED  

**Fix:**  
Use:
```ts
project?.id ?? ''
```

---

## 🟠 UI ERRORS

### UI-01 — Sidebar Overlapping Main Content
**Status:** ✅ CONFIRMED  

**Fix:**  
Add `ml-64` to layout.

---

### UI-02 — DPR Table Stuck on Loading
**Status:** ✅ CONFIRMED  

**Fix:**  
Add error handling + timeout fallback.

---

### UI-03 — Audit Log Theme Mismatch
**Status:** ✅ CONFIRMED  

**Fix:**  
Apply dark theme styles.

---

### UI-04 — CTA Button Color Inconsistency
**Status:** ✅ CONFIRMED  

**Fix:**  
Use `bg-orange-500`.

---

### UI-05 — Dashboard Charts Show "No data"
**Status:** ✅ CONFIRMED  

**Fix:**  
Debug API + props.

---

### UI-06 — Dashboard Stat Cards Hidden
**Status:** ✅ CONFIRMED  

**Fix:**  
Same as UI-01.

---

### UI-07 — TEAM Link → 404
**Status:** ✅ CONFIRMED  

**Fix:**  
Create users page or update route.

---

## 🟡 MINOR / LOW PRIORITY

### M-01 — Petty Cash Cards Hidden
Fix: Same as UI-01

### M-02 — "SINCE LAST PC CLOSE" Shows --
Fix: Show fallback text

### M-03 — Sub-menu Styling Missing
Fix: Add padding + styling

---

## 🆕 NEW ISSUES

### NEW-01 — Vendors AG Grid Theme Issue
Fix: Use `ag-theme-quartz-dark`

### NEW-02 — Projects Page Blank on Direct Navigation
Fix: Add ErrorBoundary

### NEW-03 — 404 Page Unstyled
Fix: Create `app/not-found.tsx`

### NEW-04 — Error Count Accumulation
Fix: Resolved via CE-01

### NEW-05 — Persistent Error Toast
Fix: Add auto-dismiss

---

## SUMMARY TABLE

| #  | Issue ID | Severity    | Page(s)                                    | Fix Summary                                                      |
| -- | -------- | ----------- | ------------------------------------------ | ---------------------------------------------------------------- |
| 1  | UR-01    | 🔴 CRITICAL | All                                        | Increase JWT maxAge, add token refresh                           |
| 2  | CE-01    | 🔴 CRITICAL | Clients, Projects, Categories, Work Orders | Register AG Grid modules globally                                |
| 3  | UI-01    | 🔴 CRITICAL | All                                        | Add ml-64 to layout                                              |
| 4  | UR-02    | 🔴 CRITICAL | Site Overheads                             | Create page.tsx                                                  |
| 5  | UR-03    | 🔴 CRITICAL | Reports                                    | Create page.tsx                                                  |
| 6  | UR-04    | 🔴 CRITICAL | Dashboard                                  | Fix project ID handling                                          |
| 7  | NEW-01   | 🟠 HIGH     | Vendors                                    | Apply dark AG Grid theme                                         |
| 8  | NEW-02   | 🟠 HIGH     | Projects                                   | Add ErrorBoundary                                                |
| 9  | UI-02    | 🟠 HIGH     | Site Operations                            | Fix DPR API handling                                             |
| 10 | UI-03    | 🟠 HIGH     | Audit Log                                  | Apply dark theme                                                 |
| 11 | UI-07    | 🟠 HIGH     | Dashboard                                  | Fix TEAM route                                                   |
| 12 | NEW-03   | 🟠 HIGH     | 404 pages                                  | Create custom not-found page                                     |
| 13 | UI-04    | 🟡 MEDIUM   | Payment Cert                               | Fix CTA color                                                    |
| 14 | UI-05    | 🟡 MEDIUM   | Dashboard                                  | Fix chart data                                                   |
| 15 | CE-02    | 🟡 MEDIUM   | All                                        | Upgrade Next.js                                                  |
| 16 | NEW-04   | 🟡 MEDIUM   | All                                        | Fixed via CE-01                                                  |
| 17 | M-03     | 🟡 LOW      | Site Operations                            | Improve sub-menu styling                                         |
| 18 | M-02     | 🟡 LOW      | Dashboard                                  | Add fallback text                                                |
| 19 | NEW-05   | 🟢 LOW      | All (dev)                                  | Auto-dismiss toast                                               |
