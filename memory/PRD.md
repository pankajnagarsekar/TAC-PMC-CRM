# TAC-PMC React Native Expo App

## Problem Statement
Build navigation shell for TAC-PMC React Native Expo app with role-based navigation and authentication.

## Implementation Date
January 2026

## What's Been Implemented

### Core App Files (Session 2)

#### `app/_layout.tsx` - Root Layout
- Wraps app in AuthProvider and ProjectProvider
- Stack navigator for all routes

#### `app/index.tsx` - Entry Point
- Checks SecureStore for "access_token"
- Reads "user_role" and redirects:
  - admin → /(admin)/dashboard
  - supervisor → /(supervisor)/dashboard
  - no token → /login
- Platform-aware (SecureStore for native, localStorage for web)

#### `app/login.tsx` - Login Screen
- Email/password fields
- POST /api/auth/login with {email, password}
- On success: saves token as "access_token", role as "user_role"
- Redirects by role
- Inline error messages on failure
- Colors: primary #1E3A5F (button), accent #F97316, white background

### Tab Navigation (Session 1)

#### Admin Layout (`app/(admin)/_layout.tsx`)
- Bottom tabs: Dashboard, DPR, Workers, More
- Tab bar: background #1E3A5F, active #F97316

#### Supervisor Layout (`app/(supervisor)/_layout.tsx`)
- Bottom tabs: Dashboard, Attendance, DPR, Profile
- Same tab bar styling

### Nested Layouts
- `app/(admin)/dpr/_layout.tsx` - Stack for create, [id] screens
- `app/(admin)/settings/_layout.tsx` - Stack for settings sub-screens

## Files Modified/Created
1. `app/_layout.tsx` - Root layout with context providers
2. `app/index.tsx` - Auth check and redirect
3. `app/login.tsx` - Login screen
4. `app/(admin)/_layout.tsx` - Admin tab navigation
5. `app/(supervisor)/_layout.tsx` - Supervisor tab navigation
6. `app/(admin)/dpr/_layout.tsx` - DPR stack
7. `app/(admin)/settings/_layout.tsx` - Settings stack

## Session 3 - Import Fixes
- Fixed `VersionSelector` import in `app/(admin)/dpr/[id].tsx` (was named import, should be default import)
- Verified all other imports are correct (contexts, components, constants, services)
- All files use `EXPO_PUBLIC_BACKEND_URL` environment variable for API calls

## Import Pattern Summary
- Contexts: `../../contexts/AuthContext`, `../../contexts/ProjectContext`
- Components: `../../components/ui` (Card, etc.), `../../components/ScreenHeader`
- Constants: `../../constants/theme` (Colors, Spacing, FontSizes, BorderRadius)
- Services: `../../services/apiClient` (apiClient, projectsApi, codesApi, usersApi, etc.)
- Types: `../../types/api`

## Session 4 - Shared DPR Component

### Created: `components/DPRForm.tsx`
- Shared DPR creation component used by both Admin and Supervisor
- Voice recording with speech-to-text transcription
- Photo capture/gallery with collapsible cards
- Enforces minimum 4 photos with required captions
- Uses `EXPO_PUBLIC_BACKEND_URL` for API calls
- Shows loading state during submit
- PDF download/sharing on success

### Updated: `app/(admin)/dpr/create.tsx`
- Now uses shared DPRForm component
- Two-step flow: 1) Select project + optional fields, 2) DPR form
- Passes extra payload (weather, manpower) to DPRForm
- Same UI/UX as Supervisor DPR

### Updated: `app/(supervisor)/dpr.tsx`  
- Now uses shared DPRForm component
- Gets project from ProjectContext
- Simplified to ~60 lines

### Key Features (both screens):
- Voice summary with multi-language transcription
- Collapsible photo cards with caption validation
- Min 4 photos required before submit
- PDF generation and sharing on success
- Loading/error states

## Backlog
- P1: Add badge indicators for notifications in tab bar
- P2: Add "forgot password" functionality
