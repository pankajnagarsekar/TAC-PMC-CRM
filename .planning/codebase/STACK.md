# Technology Stack

## Backend (apps/api)
- **Language**: Python 3.12+
- **Framework**: FastAPI (Modern, high-performance)
- **Database Driver**: Motor (Asynchronous MongoDB)
- **Validation**: Pydantic v2 (Strict type checking)
- **Task Queue**: Celery with Redis (Background processing)
- **Security**: 
  - JWT (pyjwt/python-jose)
  - bcrypt (Password hashing)
  - slowapi (Rate limiting)
- **Utilities**: 
  - pandas/numpy (Data processing)
  - weasyprint/reportlab (PDF generation)
  - openpyxl/xlsxwriter (Excel processing)

## Web Frontend (apps/web)
- **Framework**: Next.js 16.2.0 (App Router)
- **Library**: React 19.0.0
- **State Management**: Zustand
- **Data Fetching**: SWR (Stale-While-Revalidate)
- **Styling**: Tailwind CSS 4 (Utility-first)
- **UI Components**: 
  - Radix UI Primitives
  - Lucide React (Icons)
  - Tremor (Charts/Dashboards)
  - AG Grid React (Data tables)

## Mobile Application (apps/mobile)
- **Platform**: Expo 54.0.33 / React Native 0.81.5
- **Navigation**: Expo Router (File-based)
- **Styling**: react-native-reanimated / expo-blur
- **Storage**: @react-native-async-storage/async-storage

## Infrastructure & Tooling
- **Package Manager**: pnpm (Workspaces enabled)
- **Monorepo Orchestration**: Turbo (Build/Dev/Lint caching)
- **Runtime**: Node.js 20+
