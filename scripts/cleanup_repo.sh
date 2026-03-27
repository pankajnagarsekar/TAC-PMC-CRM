#!/usr/bin/env bash
# cleanup_repo.sh - Production-ready repository cleanup script

# Check if script is running in bash
if [ -z "$BASH_VERSION" ]; then
    echo "Error: This script must be run in bash."
    exit 1
fi

set -euo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# 1. Clean root directory
log "Cleaning root directory..."
ROOT_JUNK=(
  "clean_auth.py"
  "large_project_5k.json"
  "test_imports.py"
  "tmp_auth.py"
  "tmp_search_git.py"
  "verify_pdf_v2.py"
  "Ruflo_RESTRUCTURE_PROTO.md"
  "VERIFICATION_BUDGET_FIX.md"
  "ruflo agent swarm guidelines.md"
  "temp_repo"
  "tmp"
  ".pytest_cache"
)

for f in "${ROOT_JUNK[@]}"; do
  if [ -e "$f" ]; then
    log "Removing $f"
    rm -rf "$f"
  fi
done

# 2. Clean apps/api (Backend)
log "Cleaning apps/api..."
API_PATH="apps/api"
API_JUNK=(
  ".pytest_cache"
  ".tmp"
  "IN_PROG"
  "Python"
  "__pycache__"
)

if [ -d "$API_PATH" ]; then
  for f in "${API_JUNK[@]}"; do
    full_path="$API_PATH/$f"
    if [ -e "$full_path" ]; then
      log "Removing $full_path"
      rm -rf "$full_path"
    fi
  done
fi

# 3. Clean apps/web (Frontend)
log "Cleaning apps/web..."
WEB_PATH="apps/web"
WEB_JUNK=(
  ".next"
  ".turbo"
  "tsc_errors.log"
  "tsc_errors_final.log"
  "tsconfig.tsbuildinfo"
)

if [ -d "$WEB_PATH" ]; then
  for f in "${WEB_JUNK[@]}"; do
    full_path="$WEB_PATH/$f"
    if [ -e "$full_path" ]; then
      log "Removing $full_path"
      rm -rf "$full_path"
    fi
  done
fi

# 4. Clean apps/mobile (Mobile)
log "Cleaning apps/mobile..."
MOBILE_PATH="apps/mobile"
MOBILE_JUNK=(
  ".expo"
  ".metro-cache"
  ".turbo"
  "dist"
)

if [ -d "$MOBILE_PATH" ]; then
  for f in "${MOBILE_JUNK[@]}"; do
    full_path="$MOBILE_PATH/$f"
    if [ -e "$full_path" ]; then
      log "Removing $full_path"
      rm -rf "$full_path"
    fi
  done
fi

log "Repository cleanup complete."
