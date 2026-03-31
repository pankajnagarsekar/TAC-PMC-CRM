# 🛠️ TAC-PMC CRM Server Management Guide

This guide provides rigorous instructions on how to manage the development servers, ensure port availability, and maintain a clean runtime environment.

---

## � Step 1: Kill All Ports & Clear Processes
Before starting the servers, ensure no stale processes are occupying the required ports (3000, 3001, 8000, 27017).

### 1. Simple Process Stop
Run this in PowerShell to gracefully kill common development processes:
```powershell
Stop-Process -Name "python", "node", "mongod" -Force
```

### 2. Targeted Port Killing (Deep Clean)
If servers are stuck in the background, run these commands to find and kill the specific PID on each port:
```powershell
# Kill Web Frontend (3000)
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Kill Mobile App (3001)
Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Kill API Server (8000)
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# Kill MongoDB (27017)
Get-NetTCPConnection -LocalPort 27017 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

---

## 🧹 Step 2: Flush Cache & Refresh Dependencies
If you experience environment drift or build errors, clear the artifact caches:

```bash
# From project root
rm -rf apps/web/.next
rm -rf apps/api/__pycache__
rm -rf apps/mobile/.expo
rm -rf node_modules
pnpm install
```

---

## 🚀 Step 3: Start All Servers
Follow this order to ensure dependencies (database) are available before the application layers start.

### A. Start Database (MongoDB) - [MANDATORY FIRST]
Open a dedicated terminal and run:
```powershell
& "C:\Program Files\MongoDB\Server\8.2\bin\mongod.exe" --dbpath ./tmp/mongodb --port 27017
```

### B. Start Application Stack (App, API, Web)
Once MongoDB is running, run the following in the project root:
```bash
pnpm start-all
```
*This command uses `concurrently` to launch:*
1.  **API (Backend)**: `apps/api` on port 8000.
2.  **Web Frontend**: `apps/web` on port 3000.
3.  **Mobile App**: `apps/mobile` on port 3001.

---

## 🔄 Refreshing Servers
To "Refresh" without a deep clean:
1.  **Stop**: Click into the `pnpm start-all` terminal and press `Ctrl + C`.
2.  **Start**: Run `pnpm start-all` again.
3.  **Hot Reload**: Most changes to `.py`, `.ts`, or `.tsx` files trigger automatic reloads without needing a restart.

---

## 🍱 Summary Table
| Service | Directory | Port | Runtime |
| :--- | :--- | :--- | :--- |
| **MongoDB** | System | 27017 | mongod |
| **API (Backend)** | `apps/api` | 8000 | Python/Uvicorn |
| **Web Frontend** | `apps/web` | 3000 | Next.js/Node |
| **App (Mobile)** | `apps/mobile` | 3001 | Expo/Node |
