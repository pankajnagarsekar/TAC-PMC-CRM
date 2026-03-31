TAC PMC CRM Unique Issues Report

CRITICAL ISSUES

BUG 001 Reports page not rendering
Reports route redirects to dashboard because page file is missing
Fix create app admin reports page

BUG 002 Projects list API failure
Projects API not returning data causing empty list
Fix repair api projects endpoint and error handling

BUG 003 Project detail page infinite loading
Project detail fetch never resolves and loading state not cleared
Fix add proper try catch and finally to stop loading

BUG 004 Categories grid stuck loading
Row data not set causing infinite loading state
Fix set empty array on error and success mapping

BUG 005 Site operations grids not loading
DPR and attendance grids stuck due to missing row data
Fix ensure API response sets row data or empty array

BUG 006 Work orders list blank after loading
Component not rendering after loading completes
Fix always render grid with fallback state

BUG 007 Site overheads add transaction not working
Button click has no handler or modal not wired
Fix attach onClick and render modal

BUG 008 Voice logs not loading
Recording list fetch failing or not updating state
Fix add error and empty state handling

BUG 009 Modal rendering off screen
All modals positioned outside viewport due to CSS issue
Fix center modal using fixed position and transform

BUG 010 Dashboard NaN percentage
Division by zero causing NaN display
Fix guard against zero values

BUG 011 Duplicate petty cash stat card
Same stat card rendered twice
Fix remove duplicate and restore correct metric

BUG 012 Retention amount negative zero
Calculation displays negative zero
Fix normalize zero display

BUG 013 AG grid theme inconsistency
Some pages use light theme breaking UI consistency
Fix apply dark theme globally

BUG 014 AG grid column truncation
Column widths too small causing unreadable headers
Fix auto size columns and define min widths

BUG 015 Scheduler crash on calculation
Undefined value used with toLocaleString causing crash
Fix add null checks and validation

BUG 016 Project switcher not loading projects
Separate API call failing in modal
Fix align with main projects API and auth

BUG 017 Sidebar layout overlap
Main content hidden behind sidebar
Fix add left margin to layout

BUG 018 Missing routes causing 404
Users and site overhead pages missing
Fix create required route files

BUG 019 Charts not showing data
Dashboard charts receive no data
Fix validate API and props mapping

BUG 020 Error handling missing across app
Many components fail silently without fallback UI
Fix add consistent error boundaries and empty states

BUG 021 Session expiry too aggressive
Session expires within seconds breaking navigation
Fix increase session max age and add refresh logic

BUG 022 Next version outdated
Framework outdated warning present
Fix upgrade next package

BUG 023 404 page not styled
Default blank page shown without layout
Fix create custom not found page with layout

BUG 024 Persistent error toast
Error indicator does not auto dismiss
Fix add timeout or restrict to dev mode

BUG 025 Vendors grid theme mismatch
Vendors page uses incorrect grid styling
Fix apply consistent dark theme

BUG 026 Projects page blank on direct navigation
Page fails to render without navigation context
Fix add error boundary and handle async errors

BUG 027 Submenu styling missing
Sidebar submenu lacks indentation and active state
Fix add padding and highlight styles

BUG 028 Missing empty states
Multiple pages show blank UI instead of empty state
Fix add fallback messages for no data

BUG 029 Broken dashboard links
Links use undefined project id
Fix wait for project data before rendering links

BUG 030 Data fetch not standardized
Multiple inconsistent API handling patterns
Fix centralize fetch logic and error handling
