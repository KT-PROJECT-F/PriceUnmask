#!/bin/bash
# #244 PR 2 - Called by GitHub Actions via SSH, runs on VM
# Usage: ./deploy.sh <commit-sha>
# Example: ./deploy.sh abc123def456...

set -euo pipefail

# 0. Validate SHA first to prevent shell injection.
# SHA must be exactly 40 hex characters.
if [ $# -ne 1 ]; then
  echo "Usage: $0 <commit-sha>"
  exit 1
fi

if ! [[ "$1" =~ ^[0-9a-f]{40}$ ]]; then
  echo "ERROR: Invalid SHA. Must be 40 hex chars."
  exit 1
fi

# 1. Run everything as the priceunmask user.
# /opt/priceunmask is mode 750, .env is mode 640 root:priceunmask,
# and shared/data is owned by priceunmask. Running as any other user
# would fail to read or write these paths.
if [ "$(whoami)" != "priceunmask" ]; then
  echo "Re-running as priceunmask user..."
  exec sudo -u priceunmask "$0" "$@"
fi

COMMIT_SHA="$1"

APP_DIR="/opt/priceunmask"
CURRENT="$APP_DIR/current"
RELEASES="$APP_DIR/releases"
SHARED="$APP_DIR/shared"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
NEW_RELEASE="$RELEASES/$TIMESTAMP"
PREV_RELEASE="$(readlink "$CURRENT" || echo "")"

# Runs as priceunmask user (re-exec above). All files owned by priceunmask.
mkdir -p "$RELEASES" "$SHARED/data/exports"

# 1. Clone the exact commit, not the tip of the dev branch.
# Deploying the branch tip is unsafe: a merge during deploy
# would silently change what goes live.
git clone --depth 50 https://github.com/KT-PROJECT-F/PriceUnmask.git "$NEW_RELEASE"
cd "$NEW_RELEASE"
git checkout "$COMMIT_SHA"
git rev-parse HEAD

# Shared files live outside releases so pruning never deletes them.
ln -sfn "/etc/priceunmask/priceunmask.env" "$NEW_RELEASE/.env"

# Clone brings a real data/ folder (data/snapshots/ is tracked).
# Remove it first, otherwise ln creates NEW_RELEASE/data/data
rm -rf "$NEW_RELEASE/data"
ln -sfn "$SHARED/data" "$NEW_RELEASE/data"

# Per-release venv
python3 -m venv "$NEW_RELEASE/.venv"
"$NEW_RELEASE/.venv/bin/pip" install -r "$NEW_RELEASE/requirements.txt"

# 2. DB backup.
# export_db.py takes no arguments and has no --out flag.
# It reads DATABASE_URL from settings (.env) and writes to ./data/exports/.
# Which is a symlink to shared/data/exports/.
# First deploy: no .db file yet, so export_db would fail + set -e kills deploy.
# Skip backup if no DB exists.
if ls "$SHARED/data/"*.db >/dev/null 2>&1; then
  echo "Backing up DB..."
  cd "$NEW_RELEASE"
  "$NEW_RELEASE/.venv/bin/python" -m backend.devtools.export_db
else
  echo "First deploy - no DB file yet, skipping backup"
fi

# 3. Point current at the new release.
ln -sfn "$NEW_RELEASE" "$CURRENT"

# 4. Restart the API.
# Wrapped in if-! so a restart failure rolls back instead of
# stopping the script mid-deploy with the broken release live.
# Service name per Hemalatha PR #251: priceunmask.service
if ! sudo systemctl restart priceunmask.service; then
  echo "Restart FAILED - Rolling back to $PREV_RELEASE"
  if [ -z "$PREV_RELEASE" ]; then
    echo "ERROR: No previous release to rollback to. Manual fix needed!"
    exit 1
  fi
  ln -sfn "$PREV_RELEASE" "$CURRENT"
  sudo systemctl restart priceunmask.service || true
  exit 1
fi

sudo systemctl reload nginx || true
# The collector also runs from current, so restart it too.
# Otherwise it keeps running from a release we are about to prune.
# try-restart: if collector was stopped on purpose, don't start it again.
sudo systemctl try-restart priceunmask-collector.service || true

# 5. Health-check with a per-request timeout so curl cannot hang forever
check_health() {
  for i in $(seq 1 30); do
    if curl --max-time 5 -f http://127.0.0.1:8000/api/health; then
      return 0
    fi
    echo "Waiting... $i/30"
    sleep 2
  done
  return 1
}

if check_health; then
  echo "Deploy PASSED"
else
  echo "FAILED - Rolling back to $PREV_RELEASE"
  # 6. On the very first deploy there is no previous release to roll back to.
  if [ -z "$PREV_RELEASE" ]; then
    echo "ERROR: No previous release to rollback to. current is broken, manual fix needed!"
    exit 1
  fi
  ln -sfn "$PREV_RELEASE" "$CURRENT"
  sudo systemctl restart priceunmask.service
  sudo systemctl try-restart priceunmask-collector.service || true
  if check_health; then echo "Rollback PASSED"; exit 1; fi
  echo "Rollback FAILED - manual fix needed!"
  exit 1
fi

# 7. Keep only the last 3 releases - venvs are large.
# Safe now because the collector was restarted from current above.
# Never delete PREV_RELEASE or NEW_RELEASE even if it fails leave half-built folders.
cd "$RELEASES"
ls -t | tail -n +4 | while read -r d; do
  if [ "$RELEASES/$d" != "$PREV_RELEASE" ] && [ "$RELEASES/$d" != "$NEW_RELEASE" ]; then
    rm -rf "$RELEASES/$d"
  fi
done

echo "Done! Kept last 3 releases. Deployed $COMMIT_SHA"