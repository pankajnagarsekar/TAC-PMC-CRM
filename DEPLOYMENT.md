# TAC-PMC-CRM Deployment Guide

Complete instructions for local development and production deployment to Render + Vercel.

---

## Part 1: Local Development with Docker

### Prerequisites
- Docker Desktop installed and running
- Git configured
- MongoDB Atlas account (or local MongoDB)
- Node.js 20+ and pnpm installed
- Python 3.11+

### Quick Start (5 minutes)

#### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/TAC-PMC-CRM.git
cd TAC-PMC-CRM

# Install dependencies
pnpm install
```

#### 2. Create Environment Files

**apps/api/.env** (API Backend)
```env
MONGO_URL=mongodb://mongo:27017
DB_NAME=tac_pmc_crm
JWT_SECRET_KEY=your-secret-key-here-min-32-chars
ENVIRONMENT=development
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:3001"]
REDIS_URL=
OPENAI_API_KEY=
STORAGE_PATH=storage
```

**apps/web/.env.local** (Next.js Frontend)
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

**apps/mobile/.env** (React Native)
```env
EXPO_PUBLIC_BACKEND_URL=http://localhost:8000
```

#### 3. Start All Services with Docker Compose
```bash
# From project root
docker compose up

# Services will be available at:
# API:    http://localhost:8000
# Web:    http://localhost:3000
# Mongo:  localhost:27017
```

#### 4. Seed Production Data
```bash
cd apps/api
python scripts/seed_production.py
```

**Available Logins:**
- Admin: `admin@tacpmc.com` / `Admin@1234`
- Supervisor: `supervisor@tacpmc.com` / `Supervisor@1234`
- Client: `client@tacpmc.com` / `Client@1234`

#### 5. Verify Services
```bash
# API Health Check
curl http://localhost:8000/system/health

# API Docs
open http://localhost:8000/docs

# Web App
open http://localhost:3000
```

### Local Development Workflow

#### Start Development Mode (Without Docker)
```bash
# Terminal 1: API (Python)
cd apps/api
python -m uvicorn app.main:app --reload

# Terminal 2: Web (Next.js)
cd apps/web
npm run dev

# Terminal 3: Mobile (Expo)
cd apps/mobile
npm run dev
```

#### Running Tests
```bash
# API tests
cd apps/api
pytest tests/

# Web tests
cd apps/web
npm run test

# Type checking
npx tsc --noEmit
```

#### Building Locally
```bash
# Build all
pnpm build

# Verify Docker builds
docker build -t tac-pmc-api apps/api/
docker build -t tac-pmc-web --build-arg NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 -f apps/web/Dockerfile .
```

---

## Part 2: Production Deployment to Render + Vercel

### Architecture
```
┌─────────────────┐
│  Vercel (Web)   │──────┐
└─────────────────┘      │
                         │
                    ┌────▼────┐
                    │  Render  │
                    │   (API)  │
                    └────┬────┘
                         │
                    ┌────▼──────────┐
                    │ MongoDB Atlas  │
                    │   (Database)   │
                    └───────────────┘
```

### Step 1: Prepare MongoDB Atlas

#### 1.1 Create Cluster
1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create new cluster (free tier available)
3. Create database user with strong password
4. Whitelist IP: For Render free tier, use `0.0.0.0/0` (all IPs)
5. Get connection string: `mongodb+srv://user:password@cluster.mongodb.net/tac_pmc_crm`

#### 1.2 Run Initial Seed
```bash
# Set connection string
export MONGO_URL="mongodb+srv://user:pass@cluster.mongodb.net"

# Seed production data
python scripts/seed_production.py
```

### Step 2: Deploy API to Render

#### 2.1 Create Render Web Service
1. Sign up at [render.com](https://render.com)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `tac-pmc-api`
   - **Environment:** `Python 3.11`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory:** `apps/api`
   - **Publish Port:** `8000` → `$PORT`

#### 2.2 Set Environment Variables
In Render dashboard → Settings → Environment:
```
MONGO_URL=mongodb+srv://user:pass@cluster.mongodb.net/tac_pmc_crm
DB_NAME=tac_pmc_crm
JWT_SECRET_KEY=<generate: openssl rand -hex 32>
ENVIRONMENT=production
ALLOWED_ORIGINS=["https://your-vercel-app.vercel.app"]
STORAGE_PATH=/tmp/storage
```

#### 2.3 Deploy
1. Click **Create Web Service**
2. Render automatically deploys from main branch
3. Wait for build to complete (~3 minutes)
4. Get API URL: `https://tac-pmc-api.onrender.com`
5. Test: `curl https://tac-pmc-api.onrender.com/system/health`

**Note:** Free tier spins down after 15 min inactivity. Upgrade to paid ($7/mo) to keep always-on.

### Step 3: Deploy Web to Vercel

#### 3.1 Create Vercel Project
1. Go to [vercel.com](https://vercel.com)
2. Click **Add New** → **Project**
3. Select your GitHub repository
4. Configure:
   - **Framework:** Next.js
   - **Root Directory:** `apps/web`
   - **Build Command:** `pnpm build`
   - **Output Directory:** `.next`

#### 3.2 Set Environment Variables
In Vercel → Settings → Environment Variables:
```
NEXT_PUBLIC_BACKEND_URL=https://tac-pmc-api.onrender.com
```

#### 3.3 Deploy
1. Click **Deploy**
2. Vercel auto-deploys from main branch
3. Wait for build (~2 minutes)
4. Get Web URL: `https://your-project.vercel.app`

#### 3.4 Update API CORS
In Render dashboard → Environment Variables, update:
```
ALLOWED_ORIGINS=["https://your-project.vercel.app"]
```
Then click **Redeploy** on the Web Service.

### Step 4: Publish Mobile App (Expo Go)

#### 4.1 Setup Expo Account
```bash
npx expo login
# Enter your Expo username and password
```

#### 4.2 Update Backend URL
Edit `apps/mobile/.env`:
```env
EXPO_PUBLIC_BACKEND_URL=https://tac-pmc-api.onrender.com
```

#### 4.3 Publish
```bash
cd apps/mobile

# For internal testing (Expo Go)
npx expo publish

# Or build and submit
npx eas build --platform android  # or ios
npx eas submit --platform android
```

Share the Expo link with team for testing.

---

## Part 3: Post-Deployment Checklist

### Verify All Services

#### API Health Check
```bash
curl https://tac-pmc-api.onrender.com/system/health
curl https://tac-pmc-api.onrender.com/docs
```

#### Web App
```bash
open https://your-project.vercel.app
# Login as: admin@tacpmc.com / Admin@1234
```

#### Mobile App
```bash
# Use Expo Go on your phone
# Scan QR code from: npx expo start
```

### Database Verification
```bash
# Connect to MongoDB Atlas
mongosh "mongodb+srv://user:pass@cluster.mongodb.net/tac_pmc_crm"

# Check collections
show collections

# Verify users
db.users.find().pretty()

# Check projects
db.projects.find().pretty()
```

### Performance Checks
- API response time: < 500ms
- Web page load: < 3s (First Contentful Paint)
- Database query: < 100ms

### Security Checklist
- ✅ JWT_SECRET_KEY is random (32+ chars)
- ✅ MONGO_URL uses strong password
- ✅ MongoDB whitelists correct IPs
- ✅ CORS allows only deployed domains
- ✅ No .env files committed to git
- ✅ HTTPS enforced for all endpoints

---

## Part 4: Monitoring & Troubleshooting

### Monitor Render API

**View Logs:**
```bash
# In Render dashboard → Logs
# Filter by date/severity
```

**Common Issues:**

| Error | Cause | Fix |
|-------|-------|-----|
| `SSL handshake failed` | MongoDB IP not whitelisted | Add `0.0.0.0/0` to Atlas or use Private Endpoint |
| `ModuleNotFoundError` | Missing dependency | Update requirements.txt, redeploy |
| `Cold start > 30s` | Free tier spin-up | Upgrade to paid tier for always-on |
| `CORS error` | Domain not in ALLOWED_ORIGINS | Update env var, redeploy |

**Restart Service:**
```bash
# In Render dashboard
Settings → Restart Web Service
```

### Monitor Vercel Web

**View Logs:**
```bash
# In Vercel dashboard → Deployments → Logs
```

**Common Issues:**

| Error | Cause | Fix |
|-------|-------|-----|
| `NEXT_PUBLIC_BACKEND_URL not set` | Env var missing | Add to Vercel → Settings |
| `API connection timeout` | Backend unreachable | Verify Render API is running |
| `Build fails: TypeScript errors` | Type checking fails | Fix errors in `apps/web/src` |

**Rollback Deployment:**
```bash
# In Vercel dashboard → Deployments
# Click "Rollback" on previous deployment
```

---

## Part 5: Continuous Deployment

### GitHub Actions CI/CD

Push code to main branch → Automatic deployment:

```yaml
# .github/workflows/ci.yml (provided)
- API: Lint, test, build Docker image
- Web: Lint, type check, build
- Both: Deploy to Render/Vercel
```

**View CI Status:**
- GitHub → Actions tab
- Render → Build/Deploy logs
- Vercel → Deployments tab

---

## Part 6: Scaling & Upgrades

### When You Need to Scale

| Component | Free | Upgrade |
|-----------|------|---------|
| **API (Render)** | $0 (spins down) | $7/mo (always-on) |
| **Web (Vercel)** | $0 | $20/mo (priority support) |
| **Database (MongoDB)** | 512MB shared | M2+ cluster ($57+/mo) |
| **Storage** | None | S3 ($1-5/mo typical usage) |

### File Upload Support
Currently: No persistent storage (ephemeral on Render)
To enable: Add AWS S3 bucket, update API configuration

### Caching & Performance
- Vercel: Edge caching enabled by default
- API: Add Redis add-on for session/rate limit caching
- Database: Indexes optimized for common queries

---

## Appendix: Quick Reference

### Environment Variables Summary

**API (.env)**
```env
MONGO_URL=mongodb+srv://user:pass@host/db
DB_NAME=tac_pmc_crm
JWT_SECRET_KEY=<random 32+ chars>
ENVIRONMENT=production
ALLOWED_ORIGINS=["https://web-url.vercel.app"]
```

**Web (.env.local)**
```env
NEXT_PUBLIC_BACKEND_URL=https://api-url.onrender.com
```

**Mobile (.env)**
```env
EXPO_PUBLIC_BACKEND_URL=https://api-url.onrender.com
```

### Common Commands

```bash
# Local
docker compose up                    # Start all services
python scripts/seed_production.py    # Seed data
curl http://localhost:8000/docs     # API docs

# Deployment
git push origin main                 # Auto-deploy to Render/Vercel
curl https://api-url.onrender.com/health  # Test API

# Monitoring
mongosh "mongodb+srv://..."          # Connect to MongoDB
npx expo start                       # Expo dev server
npm run build                        # Build locally before push
```

### Support Links

- **Render Docs:** https://render.com/docs
- **Vercel Docs:** https://vercel.com/docs
- **MongoDB Atlas:** https://docs.atlas.mongodb.com
- **Expo Docs:** https://docs.expo.dev
- **Docker:** https://docs.docker.com

---

**Last Updated:** 2026-03-30
**Status:** Production Ready
