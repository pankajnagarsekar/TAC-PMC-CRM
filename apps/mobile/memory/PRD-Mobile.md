# TAC-PMC-CRM Mobile App PRD (Product Requirements Document)

## 1. Executive Summary
The TAC-PMC-CRM Mobile App serves as the on-the-go portal for the TAC-PMC Customer Relationship Management system. Built with a Luxury Industrial design language, the app facilitates field operations, reporting, project tracking, and client updates.

This document serves as a "locked" reference of the **existing** app flow and architecture. Any AI agent or developer modifying the codebase must consult this document to ensure existing flows are preserved and not broken when adding new features.

## 2. Technical Stack
- **Framework:** React Native with Expo
- **Routing:** Expo Router (File-based routing)
- **Language:** TypeScript
- **State Management & Contexts:** React Context (AuthContext, ProjectContext, ThemeContext)
- **API Communication:** Custom API Client (`apiClient.ts`) interacting with a Python FastAPI Backend.
- **Package Manager:** pnpm (monorepo environment via Turbo)

## 3. User Roles & Authentication Flow
The application has three sovereign roles, each with its own isolated stack and permission boundaries.

### Authentication Flow (`apps/mobile/app/login.tsx` & `index.tsx`)
1. **Login:** Users authenticate using email and password.
2. **Auth Context Check:** The root index component checks the user's role stored in the `AuthContext`.
3. **Role-Based Redirection:**
   - **Admin:** Routed to `/(admin)/projects` or `/(admin)/dashboard`.
   - **Supervisor:** Routed to `/(supervisor)/dashboard`.
   - **Client:** Routed to `/(client)/dashboard`.
4. **Layout Protection:** Each role has a specific Layout file (`_layout.tsx`) that enforces strict route guarding. If a user tries to access a route outside their role scope, they are instantly redirected to their respective home screen or forced to log out.

---

## 4. Features & User Flows By Role

### 4.1 Admin Role (`/(admin)`)
The Admin role has the most comprehensive access to project tracking, financial oversight, team management, and global settings. The Admin tab navigation consists of Dashboard, Projects, DPR (Daily Progress Reports), Attendance, Workers, Site Funds, OCR, Notifications, and Settings.

**Key Flows:**
- **Project Selection:** Admins can view a bird's-eye view of all active projects (budget stats, DPR counts, completion percentage) and tap a card to enter project-scoped mode (`/(admin)/select-project.tsx`).
- **Dashboard:** Project dashboard showing deep metrics.
- **DPR Management:**
  - View list of DPRs (`dpr/index.tsx`).
  - View DPR details (`dpr/[id].tsx`).
  - Create new DPRs using a shared Form component (`dpr/create.tsx`).
- **Worker Management:**
  - **Worker Log (`worker-log.tsx`):** Track daily worker logs. Includes fields like Vendor Name (Autocomplete), Workers Count, and Purpose of Work.
  - **Workers Report (`workers-report.tsx`):** A report engine to analyze worker logs across projects with various filters.
- **Site Funds / Petty Cash (`petty-cash.tsx`):** View unified petty cash and site overheads. Math and logic flags are strictly server-computed.
- **OCR (`ocr.tsx`):** Scanner for invoices with data extraction functionality.
- **Attendance View (`attendance-view.tsx`):** View attendance records across two tabs: Supervisor Attendance (Selfies/GPS) and Worker Attendance.
- **Notifications (`notifications.tsx`):** Centralized hub to view alerts, including DPR submissions.
- **Settings (`settings/_layout.tsx`):** Comprehensive global settings including Users management, Activity Codes, Organization config, Currency, Privacy, and Terms.

### 4.2 Supervisor Role (`/(supervisor)`)
Supervisors are field operatives. Their workflow is highly task-driven and revolves around site operations. The primary flow involves Check-in → Select Project → Manage Operations.

**Key Flows:**
- **Dashboard:** Step-by-step workflow tracking.
- **Attendance (`attendance.tsx`):**
  - **Check-in:** Mandatory check-in requiring a selfie and GPS location capture.
  - **Check-out:** Typically occurs after completing daily operations/DPR submission.
- **Project Selection (`select-project.tsx`):** Select a specific project to associate the day's logs and reports.
- **DPR Creation (`dpr.tsx`):** Submits Daily Progress Reports (uses the shared `DPRForm` component). Requires a minimum of 4 photos.
- **Worker Log (`worker-log.tsx`):** Input daily worker counts and activities.
- **Voice Log (`voice-log.tsx`):** Record voice notes for quick daily updates.
- **Profile (`profile.tsx`):** Limited profile access; allows for password changes and viewing attendance history.

### 4.3 Client Role (`/(client)`)
Clients have read-only access to their specific projects to monitor progress and view reports.

**Key Flows:**
- **Dashboard (`dashboard.tsx`):** Provides a high-level overview of the client's projects, timeline progression, and core metrics. Relies on client permission settings.
- **Reports (`reports.tsx`):** Phase 7 Parity reporting hub.
  - Clients select a project from chips.
  - Generates downloadable/shareable PDF reports (e.g., Weekly Progress, Monthly Summary, Payment Certificates).
  - Uses native file system (`expo-file-system`) and sharing API (`expo-sharing`).

---

## 5. Core Shared Components & Architecture Rules
- **UI System (`components/ui/`):** Custom standard UI components (`Card`, `Input`, `Button`, `BlueprintGrid`) ensuring a consistent Luxury Industrial theme.
- **ThemeContext (`contexts/ThemeContext.tsx`):** Centralized theming defining Colors, Spacing, Shadows, FontSizes, and BorderRadius. Used universally across all components.
- **DPRForm (`components/DPRForm.tsx`):** The engine for submitting Daily Progress Reports, shared between Admins and Supervisors. Features photo uploads (minimum 4) and handles multipart form submissions.
- **Zero Client-Side Math Rule:** Specially enforced in financial modules (e.g., Petty Cash). All balance and logic flag computations are handled explicitly by the FastAPI backend to ensure absolute data consistency.

## 6. AI Agent Guidelines for Future Development
- **Do not bypass role routing:** The `_layout.tsx` guards for Admin, Supervisor, and Client must remain intact. If you add a new screen, ensure it lives within the correct scoped folder.
- **Reuse UI Components:** Do not use plain `View` or `TouchableOpacity` if a standard `Card` or `Button` from `components/ui` fits the use case.
- **Respect Backend Sovereignty:** Follow the "Zero client-side math" rule. If a new calculation is needed, the API must be updated to return the calculated value.
- **Theme Alignment:** Any new styles should exclusively use variables provided by the `useTheme` hook (Colors, Spacing, etc.). Hardcoded colors (other than pure overrides for icons) are discouraged.