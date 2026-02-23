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

## Backlog
- P1: Add badge indicators for notifications in tab bar
- P2: Add "forgot password" functionality
