# 🛠️ TAC-PMC CRM Server Management Guide

This guide provides instructions on how to manage the development servers for the TAC-PMC CRM project.

## 🚀 How to Start All Servers

To start the entire ecosystem (Backend, Web, and Database) at once, you can use the following command from the project root:

```bash
pnpm start-all
```

> [!NOTE]
> Ensure MongoDB is installed on your system. If it's not running as a service, refer to the individual start commands below.

### 🍱 Individual Start Commands

If you prefer to start services separately:

1.  **Database (MongoDB)**:
    ```powershell
    & "C:\Program Files\MongoDB\Server\8.2\bin\mongod.exe" --dbpath ./tmp/mongodb --port 27017
    ```
2.  **Backend (API)**:
    ```bash
    cd apps/api
    python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
    ```
3.  **Web (Frontend)**:
    ```bash
    cd apps/web
    pnpm dev
    ```

---

## 🛑 How to Stop All Running Servers

### 1. Using the Terminal
If you started the servers in a terminal (using `pnpm start-all` or individual commands), you can stop them by pressing:
**`Ctrl + C`** in the respective terminal window.

### 2. Force Stop (Windows Cleanup)
If servers are stuck or running in the background, you can force stop them using these PowerShell commands:

*   **Stop Backend & Web**:
    ```powershell
    Stop-Process -Name "python", "node" -Force
    ```
*   **Stop MongoDB**:
    ```powershell
    Stop-Process -Name "mongod" -Force
    ```

---

## 🔄 How to Refresh Servers

Refreshing is typically needed when dependencies change or the environment becomes unstable.

### 1. Hot Reloading (Automatic)
The development servers are configured with **Hot Reload**:
- **Backend**: Restarts automatically when [.py](file:///d:/_repos/TAC-PMC-CRM/tmp_auth.py) files are saved.
- **Web**: Re-compiles automatically when [.tsx](file:///d:/_repos/TAC-PMC-CRM/apps/web/src/app/login/page.tsx), [.ts](file:///d:/_repos/TAC-PMC-CRM/apps/web/next-env.d.ts), or `.css` files are saved.

### 2. Total Refresh (Hard Restart)
If you encounter persistent errors after a code change:
1.  **Stop all servers** (using the commands above).
2.  **Clear Caches** (optional but recommended):
    ```bash
    # From project root
    rm -rf apps/web/.next
    rm -rf apps/api/__pycache__
    ```
3.  **Re-install Dependencies** (if [package.json](file:///d:/_repos/TAC-PMC-CRM/package.json) changed):
    ```bash
    pnpm install
    ```
4.  **Start all servers** again (`pnpm start-all`).

### 3. Database Reset (Caution!)
To reset the database to a clean state:
```bash
cd apps/api
python seed.py
```
