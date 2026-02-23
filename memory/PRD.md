# TAC-PMC React Native Expo Navigation Shell

## Problem Statement
Build navigation shell for TAC-PMC React Native Expo app with role-based bottom tab navigation.

## Implementation Date
January 2026

## What's Been Implemented

### Admin Layout (`app/(admin)/_layout.tsx`)
- Bottom tabs: Dashboard (grid-outline), DPR (document-text-outline), Workers (people-outline), More (ellipsis-horizontal-outline)
- Tab bar: background #1E3A5F, active #F97316
- Auth check via SecureStore + AuthContext
- Hidden screens for notifications, ocr, petty-cash

### Supervisor Layout (`app/(supervisor)/_layout.tsx`)
- Bottom tabs: Dashboard (home-outline), Attendance (finger-print-outline), DPR (document-text-outline), Profile (person-outline)
- Same tab bar styling
- Auth check via SecureStore + AuthContext
- Hidden screens for select-project, worker-log, voice-log

### Nested Layouts
- `app/(admin)/dpr/_layout.tsx` - Stack for create, [id] screens
- `app/(admin)/settings/_layout.tsx` - Stack for settings sub-screens

## Technical Details
- Uses expo-router Tabs component
- Imports AuthContext from contexts/AuthContext.tsx
- Imports ProjectContext from contexts/ProjectContext.tsx (available but not actively used in layouts)
- Ionicons from @expo/vector-icons

## Files Created
1. `/app/mobile/frontend/app/(admin)/_layout.tsx`
2. `/app/mobile/frontend/app/(supervisor)/_layout.tsx`
3. `/app/mobile/frontend/app/(admin)/dpr/_layout.tsx`
4. `/app/mobile/frontend/app/(admin)/settings/_layout.tsx`

## Backlog
- P1: Add badge indicators for notifications in tab bar
- P2: Add loading states during auth check
