# Project Structure

## Root Layout
```
TAC-PMC-CRM/
├── apps/
│   ├── api/           # Python FastAPI backend
│   ├── web/           # Next.js frontend
│   └── mobile/        # React Native (Expo) mobile
├── packages/
│   ├── types/         # Shared TypeScript types
│   └── ui/            # Shared UI library
├── .planning/         # GSD Project state and codebase map
├── .agents/           # RuFlo swarm and agent configs
├── scripts/           # Root-level automation scripts
├── tools/             # Custom CLI tools
├── .mcp.json          # MCP configuration
└── turbo.json         # Monorepo task definitions
```

## Backend Detail (`apps/api/app/`)
- `api/v1/`: Feature-mapped routes (site, project, work_order, etc.)
- `core/`: Cross-cutting concerns (resilience, config, UOW, financial_utils)
- `db/`: MongoDB connection management
- `domain/`: Business entities
- `repositories/`: Data access implementations
- `services/`: Business logic services
- `schemas/`: Pydantic request/response models

## Web Frontend Detail (`apps/web/src/`)
- `app/`: Next.js pages and layouts
- `components/`: UI components organized by feature
- `hooks/`: Custom React hooks
- `lib/`: Shared utilities
- `store/`: Zustand state stores
- `types/`: Frontend-specific types
