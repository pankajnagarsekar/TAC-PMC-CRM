1. Backend Framework Structure (Fix This First)
Right now your backend is script-based. You need to convert it into a layered service architecture.
Use: FastAPI + Service Layer + Repository Pattern
Target Structure
apps/api/
│
├── app/
│   ├── main.py                # FastAPI entrypoint
│   ├── core/                 # config, settings, security
│   │   ├── config.py
│   │   ├── security.py
│   │
│   ├── api/                  # routes (thin layer)
│   │   ├── v1/
│   │       ├── auth_routes.py
│   │       ├── project_routes.py
│   │       ├── ocr_routes.py
│   │
│   ├── services/             # BUSINESS LOGIC (important)
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── ocr_service.py
│   │
│   ├── repositories/         # DB access only
│   │   ├── user_repo.py
│   │   ├── project_repo.py
│   │
│   ├── models/               # ORM models
│   ├── schemas/              # Pydantic DTOs
│   ├── db/
│   │   ├── session.py
│
├── scripts/                  # move your current scripts here
│   ├── seed.py
│   ├── verify_pdf.py

Rules (non-negotiable)
Routes → ONLY request/response handling
Services → ALL business logic
Repositories → ONLY DB queries
Scripts → NO business logic (only call services)

Example Flow
route → service → repository → DB

2. Centralize Business Logic
Right now your logic is scattered across:
auth.py
verify_pdf_v2.py
seed.py
OCR screen logic
This is dangerous.
Fix: Move EVERYTHING into services/
Example
❌ Current (bad)
OCR logic inside mobile or script
Auth logic inside route file
✅ Correct
services/
  ocr_service.py
  auth_service.py
  verification_service.py
Example Service
class OCRService:
   def extract_data(self, file):
       # all logic here
       return parsed_data

Key Rule
If logic is reused OR important → it goes in service layer.

3. Fix Backend ↔ Frontend Contract
Right now:
No strict API contract
Risk of breaking UI anytime
Fix: Define a single source of truth
Use:
FastAPI auto OpenAPI OR
Explicit contract via schemas

Step 1: Define Schemas
schemas/
  auth_schema.py
  project_schema.py
class LoginRequest(BaseModel):
   email: str
   password: str

class LoginResponse(BaseModel):
   token: str
   user_id: int

Step 2: Enforce in Routes
@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
   return auth_service.login(data)

Step 3: Sync Frontend
In your


Replace manual API calls with:
typed responses
consistent endpoints

Ideal Frontend API Layer
export const login = async (data: LoginRequest) => {
 return axios.post<LoginResponse>("/api/v1/login", data)
}

Golden Rule
Backend schema = contract
 Frontend MUST follow it strictly

4. Tight Integration (Web + Mobile + API)
Right now they are loosely coupled.
Fix: Make API the single backbone
Everything must depend on:
Backend API → single source of truth

Integration Plan
1. Shared API Versioning
/api/v1/
2. Shared Types (optional but powerful)
Create:
packages/types/
Define:
export interface Project {
 id: number
 name: string
}
Use in:
Web
Mobile

3. Auth Flow Unified
Same token system for web + mobile
Same endpoints
No custom hacks per platform

4. Move OCR to backend only
Mobile should NOT do logic:
Upload → backend
Backend processes
Return result

5. Remove duplication
If logic exists in:
mobile
web
script
→ move to backend service

5. Docs Drift (Not Priority — Noted)
You’re right to deprioritize.
But note this:
If you don’t fix structure now, PRD will ALWAYS drift again.

What You Should Do Next (Order)
Step 1 (Critical)
Restructure backend folders exactly as above
Step 2
Move all logic into services/
Step 3
Define schemas + enforce API contracts
Step 4
Update frontend to follow contract
Step 5
Kill duplicate logic across apps

Hard Truth
Right now your system is:
Feature-driven
Not architecture-driven
If you don’t fix this now:
Scaling will break
Bugs will multiply
Refactoring later will be painful

