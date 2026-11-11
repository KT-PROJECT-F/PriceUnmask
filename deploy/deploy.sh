#!/bin/bash
# #244 PR 2 - Called by GitHub Actions via SSH, runs on VM
# Usage: ./deploy.sh <commit-sha>
# Example: ./deploy.sh abc123def456...
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <commit-sha>"
  exit 1
fi
COMMIT_SHA="$1"

APP_DIR="/opt/priceunmask"
CURRENT="$APP_DIR/current"
RELEASES="$APP_DIR/releases"
SHARED="$APP_DIR/shared"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
NEW_RELEASE="$RELEASES/$TIMESTAMP"
PREV_RELEASE="$(readlink "$CURRENT" || echo "")"

mkdir -p "$NEW_RELEASE" "$SHARED/data/exports"

# 1. Clone the exact commit, not the tip of the dev branch.
# Deploying the branch tip is unsafe: a merge during deploy
# would silently change what goes live.
git clone --depth 50 https://github.com/PriceUnmask/PriceUnmask.git "$NEW_RELEASE"
cd "$NEW_RELEASE"
git checkout "$COMMIT_SHA"
git rev-parse HEAD

# Shared files live outside releases so pruning never deletes them.
ln -sfn "$SHARED/.env" "$NEW_RELEASE/.env"
ln -sfn "$SHARED/data" "$NEW_RELEASE/data"

# Per-release venv
python3 -m venv "$NEW_RELEASE/.venv"
"$NEW_RELEASE/.venv/bin/pip" install -r "$NEW_RELEASE/requirements.txt"

# 2. DB backup.
# export_db.py takes no arguments and has no --out flag.
# It reads DATABASE_URL from settings (.env) and writes to ./data/exports/,
# which is a symlink to shared/data/exports/.
# No "|| true" here: if the backup fails, the deploy must stop.
echo "Backing up DB..."
cd "$NEW_RELEASE"
"$NEW_RELEASE/.venv/bin/python" -m backend.devtools.export_db
cd "$APP_DIR"

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
sudo systemctl restart priceunmask-collector.service || true

# 5. Health-check with a per-request timeout so curl cannot hang forever.
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
  sudo systemctl restart priceunmask-collector.service || true
  if check_health; then echo "Rollback PASSED"; exit 1; fi
  echo "Rollback FAILED - manual fix needed!"
  exit 1
fi

# 7. Keep only the last 3 releases - venvs are large.
# Safe now because the collector was restarted from current above.
cd "$RELEASES" && ls -1t | tail -n +4 | xargs -r rm -rf
echo "Done! Kept last 3 releases. Deployed $COMMIT_SHA"