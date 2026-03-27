# System Architecture

## Architecture Philosophy
The system is built as a **Hardened Monorepo** using **Domain-Driven Design (DDD)** principles to ensure scalability and maintainability across the API, Web, and Mobile layers.

## Backend (FastAPI + DDD)
- **Domain Layer**: Pure business logic and entity definitions (`apps/api/app/domain/`).
- **Service Layer**: Orchestrates complex business operations and enforces rules (`apps/api/app/services/`).
- **Repository Pattern**: `BaseRepository` provides hardened CRUD with:
  - **Optimistic Locking**: Versioning fields to prevent race conditions.
  - **Checksum Integrity**: Validation of data consistency on updates.
- **Unit of Work (UOW)**: Ensures atomic fund allocations and financial mutations.
- **Event Sourcing**: Audit trails for all state changes.

## Frontend (Next.js + Atomic Design)
- **App Router**: File-based routing for layouts and pages.
- **Atomic Components**: Organized into Atoms, Molecules, Organisms, and Pages.
- **Server-First**: Preference for Server Components with client-side hydration via SWR for dynamic data.

## Mobile (Expo Router)
- Deeply integrated with the shared types package.
- Consistent UI/UX using the "Luxury Industrial" design tokens.

## Common Core (packages/)
- **@tac-pmc/types**: Shared TypeScript interfaces between full stack.
- **@tac-pmc/ui**: Shared UI components and design tokens.
