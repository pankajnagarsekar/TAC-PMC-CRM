# 🚀 E2E Testing Quick Start Guide

## Problem Solved ✅

**E2E tests were failing with `401 Unauthorized` errors because test user accounts didn't exist in the database.**

The database seeding now happens automatically in CI/CD before tests run. All test accounts are created with the correct roles.

---

## Running Tests Locally

### Option 1: Fully Automated (Recommended)

```bash
# Terminal 1: Start API
cd apps/api
python -m uvicorn app.main:app --reload

# Terminal 2: In a new terminal, seed database
cd apps/api
python scripts/seed_production.py

# Terminal 3: In another terminal, run tests
pnpm test:e2e
```

### Option 2: All-in-One Script

Create a script file at project root:

```bash
#!/bin/bash
# run-tests.sh

# Start API in background
cd apps/api
python -m uvicorn app.main:app --reload > /tmp/api.log 2>&1 &
API_PID=$!

# Wait for API to start
sleep 3

# Seed database
echo "Seeding database..."
python scripts/seed_production.py

# Go back to root and run tests
cd ../..
echo "Running E2E tests..."
pnpm test:e2e

# Cleanup
kill $API_PID 2>/dev/null
echo "Done!"
```

Usage:
```bash
chmod +x run-tests.sh
./run-tests.sh
```

---

## Test Credentials

These accounts are automatically created when you seed the database:

```
Admin Accounts:
  Email:    amit@thirdangleconcept.com
  Password: Admin@1234

  Email:    admin@tacpmc.com
  Password: Admin@1234

Client Account:
  Email:    client@tacpmc.com
  Password: Client@1234

Supervisor Account:
  Email:    supervisor@tacpmc.com
  Password: Supervisor@1234
```

---

## What Tests Cover

**File:** `tests/e2e/auth.spec.ts`

| Test | Login As | Expected Result |
|------|----------|-----------------|
| ADMIN login | amit@thirdangleconcept.com | ✅ Redirects to dashboard |
| ADMIN fallback | admin@tacpmc.com | ✅ Redirects to dashboard |
| CLIENT login | client@tacpmc.com | ✅ Redirects to dashboard |
| Invalid credentials | wrong@example.com | ❌ Shows error message |
| SUPERVISOR access | supervisor@tacpmc.com | ❌ Denied (role not allowed) |

---

## CI/CD Automatic Testing

The GitHub Actions workflow automatically:

1. ✅ Starts MongoDB service
2. ✅ Starts API server
3. ✅ **Seeds test database** (NEW!)
4. ✅ Verifies database is ready
5. ✅ Runs Playwright E2E tests
6. ✅ Uploads test reports as artifacts

No manual setup required — tests run automatically on every push to main.

---

## Debugging Failed Tests

### If tests fail locally:

**Step 1: Check API is running**
```bash
curl http://localhost:8000/docs
```
Should return HTML documentation page.

**Step 2: Verify database is seeded**
```bash
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['tac_pmc_crm']
    users = await db.users.count_documents({})
    print(f'Users in database: {users}')
    client.close()

asyncio.run(check())
"
```
Should show 4+ users.

**Step 3: Run a single test**
```bash
pnpm exec playwright test auth.spec.ts --debug
```
This opens the Playwright Inspector for step-by-step debugging.

### If tests fail in CI/CD:

1. Check **Workflow Run Logs** for API startup errors
2. Look at **Playwright Reports** (available as artifacts in GitHub Actions)
3. Check **MongoDB Connection** — service might not have started
4. Verify **Seed Script** ran without errors

---

## File Changes

**What was fixed:**
- ✅ `apps/api/scripts/seed_production.py` — Fixed client role from "Other" to "Client"
- ✅ `apps/api/scripts/seed.py` — Enhanced with all test users
- ✅ `tests/e2e/pom/LoginPage.ts` — Added retry logic (was already improved)
- ✅ `.github/workflows/ci.yml` — Already has seeding step

---

## Important Notes

### Database is Fresh on Each Test Run
- Seeding is **idempotent** (safe to run multiple times)
- If accounts exist, they're skipped
- If you want a clean slate, drop the database:
  ```bash
  mongo --eval "use tac_pmc_crm; db.dropDatabase()"
  ```

### Test User Passwords
- All passwords are **fixed** for testing
- Never use these in production
- Change credentials immediately before deploying

### Role-Based Access
- **Admin** role can access everything
- **Client** role has limited permissions (no Team Management)
- **Supervisor** role is denied access to web portal (mobile only)

---

## What's Next?

Now that authentication tests are stable, we can:

1. **Expand E2E Coverage**
   - Project creation and management
   - Financial transactions
   - Reporting and analytics

2. **Mobile Testing**
   - Supervisor login flows
   - DPR submission
   - Attendance tracking

3. **Performance Testing**
   - Load testing with concurrent users
   - Database query optimization
   - API response time monitoring

---

## Questions?

- **Stuck on seeding?** Check `apps/api/scripts/seed_production.py` for the complete seed logic
- **Need test accounts?** All required accounts are in the seed script
- **Looking for test data?** The seed also creates projects, tasks, and financial codes
- **Want to add more tests?** Copy the pattern from `tests/e2e/auth.spec.ts`

---

**Last Updated:** April 5, 2026
**Status:** All E2E tests passing ✅
**Test Coverage:** 5/5 authentication tests
