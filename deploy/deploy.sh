#!/bin/bash
# #244 PR 2 - Called by GitHub Actions via SSH, runs ON VPS
set -e
APP_DIR="/opt/priceunmask"
CURRENT="$APP_DIR/current"
RELEASES="$APP_DIR/releases"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
NEW_RELEASE="$RELEASES/$TIMESTAMP"
PREV_RELEASE=$(readlink "$CURRENT" || echo "")

mkdir -p "$NEW_RELEASE"
git clone --depth 1 --branch dev https://github.com/KT-PROJECT-F/PriceUnmask.git "$NEW_RELEASE"

# Per-release venv
python3 -m venv "$NEW_RELEASE/.venv"
"$NEW_RELEASE/.venv/bin/pip" install -r "$NEW_RELEASE/requirements.txt"

# DB backup - No cp, WAL mode
python3 -m backend.devtools.export_db --out "$APP_DIR/shared/backup-$TIMESTAMP.json" || true

ln -sfn "$NEW_RELEASE" "$CURRENT"
sudo systemctl restart priceunmask-api.service
sudo systemctl reload nginx || true

# Health-check with WAIT + RETRY - 30 x 2 sec = 60 sec
check_health() {
  for i in $(seq 1 30); do
    if curl -f http://127.0.0.1:8000/api/health; then return 0; fi
    echo "Waiting... $i/30"
    sleep 2
  done
  return 1
}

if check_health; then
  echo "Deploy PASSED"
else
  echo "FAILED - Rolling back to $PREV_RELEASE"
  ln -sfn "$PREV_RELEASE" "$CURRENT"
  sudo systemctl restart priceunmask-api.service
  if check_health; then echo "Rollback PASSED"; exit 1; else echo "MANUAL INTERVENTION REQUIRED - Both failed"; exit 1; fi
fi

# Keep only last 3 releases - venv large
cd "$RELEASES" && ls -1t | tail -n +4 | xargs -r rm -rf
echo "Done! Kept last 3 releases."