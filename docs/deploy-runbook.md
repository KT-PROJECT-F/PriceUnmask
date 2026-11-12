# PriceUnmask Linux VM Deployment Runbook

## 1. Purpose and scope

This runbook documents the deployment of PriceUnmask on an Ubuntu 24.04 WSL2 Linux VM.

This is a local deployment-readiness test, not a real VPS or public production deployment. Services are managed with systemd, and Nginx acts as a reverse proxy.

The procedures assume a dedicated `priceunmask` Linux service account and a release-based directory layout.

## 2. Architecture

- FastAPI application: `priceunmask.service`
- Background collector: `priceunmask-collector.service`
- Reverse proxy: Nginx
- Database: SQLite
- Persistent database location: `/opt/priceunmask/shared/data/priceunmask.db`
- Environment file: `/etc/priceunmask/priceunmask.env`
- Release directories: `/opt/priceunmask/releases/<release-id>`
- Active release: `/opt/priceunmask/current` (symbolic link)
- Python virtual environment: `/opt/priceunmask/current/.venv`

The API and collector run as separate systemd services. Both use the same environment file and database. Each release has its own Python virtual environment. The shared database and configuration remain outside the release directories.

## 3. Required Ubuntu packages

Install the required packages:

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip python3-full nginx sqlite3 curl
```

Confirm systemd is running:

```bash
ps -p 1 -o comm=
```

Expected output:

```text
systemd
```

## 4. Create the service account and application directories

Create a dedicated Linux service account:

```bash
if ! id priceunmask >/dev/null 2>&1; then
    sudo useradd --system --home /opt/priceunmask --shell /usr/sbin/nologin priceunmask
fi
```

Create the release, persistent data, backup, and configuration directories:

```bash
sudo install -d -o priceunmask -g priceunmask -m 750 /opt/priceunmask
sudo install -d -o priceunmask -g priceunmask -m 750 /opt/priceunmask/releases
sudo install -d -o priceunmask -g priceunmask -m 750 /opt/priceunmask/shared
sudo install -d -o priceunmask -g priceunmask -m 750 /opt/priceunmask/shared/data
sudo install -d -o priceunmask -g priceunmask -m 750 /opt/priceunmask/backups

sudo install -d -o root -g priceunmask -m 750 /etc/priceunmask
```
Allow the deploy script to run as `priceunmask`, and allow `priceunmask` to restart only its own services. Replace `<deploy-user>` with the Linux user that runs `deploy.sh` (on the WSL2 VM, your own user):

```bash
sudo tee /tmp/priceunmask-deploy >/dev/null <<'EOF'
<deploy-user> ALL=(priceunmask) NOPASSWD: /usr/bin/bash /tmp/deploy/deploy.sh *
priceunmask ALL=(root) NOPASSWD: /usr/bin/systemctl restart priceunmask.service, /usr/bin/systemctl try-restart priceunmask-collector.service, /usr/bin/systemctl reload nginx
EOF

sudo visudo -cf /tmp/priceunmask-deploy
sudo install -m 0440 -o root -g root /tmp/priceunmask-deploy /etc/sudoers.d/priceunmask-deploy
sudo rm -f /tmp/priceunmask-deploy
```

`visudo -cf` must print `parsed OK`. If it reports an error, stop and do not install the file.

The `/opt/priceunmask/current` path must be a symbolic link to a valid directory inside `/opt/priceunmask/releases`, not a normal application directory.

### Migrating an existing installation

This procedure is only for installations that still use a real application directory or have persistent data stored inside a release directory. If `/opt/priceunmask/current` is already a symbolic link and the shared database and persistent directories are configured, do not run this migration procedure. Verify the existing configuration and continue with the normal deployment procedure.

If `/opt/priceunmask/current` already exists as a real directory, do not overwrite it or deploy a release on top of it. Preserve the existing installation before continuing.

Before migrating:

1. Inspect the existing application directory and identify its database, snapshot files, environment configuration, and other persistent data.
2. Identify the active API and collector service units.
3. Stop the active API and collector services.
4. Confirm that nothing is still running from the old installation:

```bash
pgrep -af '[/]opt/priceunmask/' || echo "nothing running"
```
The output must be `nothing running`. If application processes are listed, stop and investigate before continuing.

5. Copy the existing database into the shared location. Run these commands while the old services are stopped.

Inspect the current installation layout before migrating:

```bash
sudo readlink /opt/priceunmask/current || true
sudo find /opt/priceunmask/current -maxdepth 3 \
    -type f -name '*.db' -not -path '*/exports/*' \
    -printf '%s bytes  %p\n'
sudo find /opt/priceunmask/shared/data -maxdepth 1 \
    -type f -name '*.db' -printf '%s bytes  %p\n'
```
**Important:** Save this database migration block into `/tmp/priceunmask-db-migrate.sh` and run it with `bash /tmp/priceunmask-db-migrate.sh`. Do not paste it into an interactive shell.

```bash
set -euo pipefail

# Paste the path printed by the find command above.
OLD_DB="/opt/priceunmask/current/data/priceunmask.db"
NEW_DB="/opt/priceunmask/shared/data/priceunmask.db"

if [ "$OLD_DB" = "$NEW_DB" ]; then
    echo "STOP: Source and destination database paths are identical."
    exit 1
fi

sudo test -s "$OLD_DB"

# Do not overwrite an existing shared database.
if sudo test -e "$NEW_DB" || sudo test -L "$NEW_DB"; then
    echo "STOP: Shared database destination already exists."
    exit 1
fi

# Ensure the shared database directory exists.
sudo install -d -o priceunmask -g priceunmask -m 750 \
    /opt/priceunmask/shared/data

# Create a consistent SQLite backup.
sudo sqlite3 "$OLD_DB" ".backup '$NEW_DB'"
sudo test -s "$NEW_DB"

sudo chown priceunmask:priceunmask "$NEW_DB"
sudo chmod 640 "$NEW_DB"

# Verify the copied database.
INTEGRITY=$(sudo -u priceunmask sqlite3 "$NEW_DB" 'PRAGMA integrity_check;')
echo "Database integrity: $INTEGRITY"

if [ "$INTEGRITY" != "ok" ]; then
    echo "STOP: Database integrity check failed."
    exit 1
fi

# Compare the old and new table row counts.
for T in products price_snapshots scrape_runs; do
    OLD_COUNT=$(sudo sqlite3 "$OLD_DB" "SELECT count(*) FROM $T;")
    NEW_COUNT=$(sudo -u priceunmask sqlite3 "$NEW_DB" "SELECT count(*) FROM $T;")

    echo "$T old=$OLD_COUNT new=$NEW_COUNT"

    if [ "$OLD_COUNT" != "$NEW_COUNT" ]; then
        echo "STOP: Row count mismatch in $T."
        exit 1
    fi
done
```

**Important:** If the backup command fails and leaves a destination file, do not rerun the script immediately. Inspect the destination and remove it only after confirming that it is an incomplete migration file and not an existing database.

The integrity check must print `ok`, and the old and new row counts must match for all three tables. If a count differs or a command fails, stop and investigate. Do not continue with the migration.

**Important:** If `NEW_DB` already exists, stop and inspect it before proceeding. Do not overwrite an existing shared database.

The `.backup` command is used to create a consistent SQLite backup. Do not manually copy an active SQLite database or its `-wal` and `-shm` files.

Identify and separately preserve or migrate snapshot files, environment configuration, and other persistent data. Renaming the application directory does not migrate these files to the shared data locations.

After completing those checks, preserve the existing application directory using:

**Important:** Save this directory preservation block into `/tmp/priceunmask-migrate.sh` and run it with `bash /tmp/priceunmask-migrate.sh`. Do not paste it into an interactive shell.

```bash
set -euo pipefail

APP_ROOT="/opt/priceunmask"
CURRENT="$APP_ROOT/current"
LEGACY="$APP_ROOT/legacy-current-$(date -u +%Y%m%d-%H%M%S)-$$"

if sudo test -L "$CURRENT"; then
    echo "STOP: current is already a symbolic link. Do not migrate it as a real directory."
    exit 1
fi

if ! sudo test -d "$CURRENT"; then
    echo "No existing real current directory found."
    echo "Continue with the normal deployment procedure."
    exit 0
fi

if sudo test -e "$LEGACY" || sudo test -L "$LEGACY"; then
    echo "STOP: Legacy destination already exists: $LEGACY"
    exit 1
fi

sudo mv -- "$CURRENT" "$LEGACY"

if ! sudo test -d "$LEGACY"; then
    echo "STOP: Legacy directory verification failed."
    exit 1
fi

echo "Existing installation preserved at: $LEGACY"
sudo ls -ld "$LEGACY"
```

Verify the preserved directory before continuing. Keep it until the new release, database, configuration, and persistent data have been verified.

**Important:** This operation only renames the existing application directory. It does not migrate the database, snapshots, environment file, or other persistent data. Migrate or preserve those separately before switching the application to the new shared locations.

**Important:** Do not paste the commands in Sections 5–8 directly into an interactive Bash shell. They use `set -euo pipefail` and `exit 1` for failure handling.

Until the deployment script is implemented in a follow-up PR, copy the Bash commands from Sections 5–8, in order, into a temporary script (for example, `/tmp/priceunmask-deploy-manual.sh`). Omit Markdown fences and expected-output examples. Review and replace all placeholder values before running it.

Run the temporary script using:

```bash
bash /tmp/priceunmask-deploy-manual.sh
```

## 5. Copy the application and install Python dependencies

```bash
set -euo pipefail

SOURCE_DIR="/path/to/priceunmask-release-check"

# Verify the repository before selecting the commit.
if ! git -C "$SOURCE_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "STOP: SOURCE_DIR is not a Git repository."
    exit 1
fi

COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"

if ! git -C "$SOURCE_DIR" cat-file -e "$COMMIT^{commit}"; then
    echo "STOP: Selected commit is invalid."
    exit 1
fi

for REQUIRED_PATH in \
    backend \
    requirements.txt \
    deploy/systemd/priceunmask.service \
    deploy/systemd/priceunmask-collector.service \
    deploy/nginx/priceunmask.conf
do
    if ! git -C "$SOURCE_DIR" cat-file -e "$COMMIT:$REQUIRED_PATH"; then
        echo "STOP: Selected commit is missing $REQUIRED_PATH."
        exit 1
    fi
done

echo "Deploying commit: $COMMIT"

APP_ROOT="/opt/priceunmask"
PREVIOUS_RELEASE=""

if sudo test -e "$APP_ROOT/current" && ! sudo test -L "$APP_ROOT/current"; then
    echo "STOP: Existing current path is not a symlink. Migrate it safely first."
    exit 1
fi

if sudo test -L "$APP_ROOT/current"; then
    PREVIOUS_RELEASE="$(sudo readlink -f "$APP_ROOT/current")" || {
        echo "STOP: Cannot resolve existing current symlink."
        exit 1
    }

    case "$PREVIOUS_RELEASE" in
        "$APP_ROOT"/releases/*)
            ;;
        *)
            echo "STOP: Existing current symlink points outside the releases directory."
            exit 1
            ;;
    esac

    if ! sudo test -d "$PREVIOUS_RELEASE"; then
        echo "STOP: Existing current symlink does not point to a valid release."
        exit 1
    fi
fi
```

This procedure deliberately deploys the selected committed revision. Uncommitted working-tree changes are not included.

### Check the existing database configuration

Before deployment, identify whether the installation already uses the shared database or still needs migration.

```bash
sudo readlink "$APP_ROOT/current" || true

sudo find -L "$APP_ROOT/current" -maxdepth 3 \
    -type f -name '*.db' -not -path '*/exports/*' \
    -printf '%s bytes  %p\n'

sudo find "$APP_ROOT/shared/data" -maxdepth 1 \
    -type f -name '*.db' \
    -printf '%s bytes  %p\n'
```

If `current` is already a symbolic link and the shared database exists, do not run the legacy database migration procedure. Verify the existing environment configuration:

```bash
sudo systemctl cat priceunmask.service
sudo systemctl cat priceunmask-collector.service
```

Inspect the `EnvironmentFile` setting shown by the service units. Check only the `DATABASE_URL` entry in that environment file. Do not display the entire file because it may contain secrets.

For the standard shared-layout installation, the expected database URL is:

```text
DATABASE_URL=sqlite:////opt/priceunmask/shared/data/priceunmask.db
```

If `current` is a real directory, follow the legacy migration procedure in Section 4 before continuing. Identify the old database from the discovery output and the old service configuration. Do not guess the database path.

Do not proceed if the database location is uncertain, the shared database already exists when a migration is required, or the existing configuration is unexpected.

### Stop the existing services

For an existing installation, confirm that GitHub Actions collection is disabled and no collector workflow run is queued or in progress before stopping the host collector.

Stop the existing collector and API services so no process continues executing code through the old `current` symlink during release activation.

```bash
if sudo systemctl is-active --quiet priceunmask-collector.service; then
    sudo systemctl stop priceunmask-collector.service
fi

if sudo systemctl is-active --quiet priceunmask.service; then
    sudo systemctl stop priceunmask.service
fi

if sudo systemctl is-active --quiet priceunmask-collector.service; then
    echo "STOP: Collector service is still active."
    exit 1
fi

if sudo systemctl is-active --quiet priceunmask.service; then
    echo "STOP: API service is still active."
    exit 1
fi
```

Do not proceed if either service fails to stop. Investigate the service state before continuing.

Confirm that no application process remains:

```bash
pgrep -af '[/]opt/priceunmask/' || echo "nothing running"
```

The output must be `nothing running`. If application processes are listed, stop and investigate before continuing.

### Create the new release

```bash
RELEASE_NAME="$(date -u +%Y%m%d-%H%M%S)-$(git -C "$SOURCE_DIR" rev-parse --short "$COMMIT")"
RELEASE_DIR="$APP_ROOT/releases/$RELEASE_NAME"

if sudo test -e "$RELEASE_DIR"; then
    echo "STOP: Release directory already exists: $RELEASE_DIR"
    exit 1
fi

sudo mkdir "$RELEASE_DIR"
sudo chown priceunmask:priceunmask "$RELEASE_DIR"
sudo chmod 750 "$RELEASE_DIR"
```

Export the selected committed source into the release directory:

```bash
git -C "$SOURCE_DIR" archive --format=tar "$COMMIT" |
    sudo tar -xf - -C "$RELEASE_DIR"

echo "$COMMIT" | sudo tee "$RELEASE_DIR/DEPLOYED_COMMIT" >/dev/null

sudo chown -R priceunmask:priceunmask "$RELEASE_DIR"
```

Create a virtual environment inside this release:

```bash
sudo -u priceunmask python3 -m venv "$RELEASE_DIR/.venv"
```

Install dependencies:

```bash
sudo -u priceunmask "$RELEASE_DIR/.venv/bin/pip" install --upgrade pip

sudo -u priceunmask "$RELEASE_DIR/.venv/bin/pip" install \
    -r "$RELEASE_DIR/requirements.txt"
```

Verify the dependencies:

```bash
sudo -u priceunmask "$RELEASE_DIR/.venv/bin/pip" check
```

Expected output:

```text
No broken requirements found.
```

### Activate the new release

```bash
if sudo test -e "$APP_ROOT/current.new" || sudo test -L "$APP_ROOT/current.new"; then
    echo "STOP: Temporary current.new path already exists."
    exit 1
fi

sudo ln -s "$RELEASE_DIR" "$APP_ROOT/current.new"

if ! sudo mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"; then
    sudo rm -f "$APP_ROOT/current.new"
    echo "STOP: Release activation failed."
    exit 1
fi
```

### Roll back if the new API is unhealthy

If the API fails to start or become healthy after activation, restore the previous release before attempting another deployment.

```bash
if [ -z "$PREVIOUS_RELEASE" ] || ! sudo test -d "$PREVIOUS_RELEASE"; then
    echo "STOP: No valid previous release is available for rollback."
    exit 1
fi

if sudo test -e "$APP_ROOT/current.rollback" || sudo test -L "$APP_ROOT/current.rollback"; then
    echo "STOP: Temporary current.rollback path already exists."
    exit 1
fi

sudo ln -s "$PREVIOUS_RELEASE" "$APP_ROOT/current.rollback"

if ! sudo mv -Tf "$APP_ROOT/current.rollback" "$APP_ROOT/current"; then
    sudo rm -f "$APP_ROOT/current.rollback"
    echo "STOP: Rollback symlink activation failed."
    exit 1
fi

sudo systemctl restart priceunmask.service

if ! curl --fail --silent --show-error --max-time 5 \
    http://127.0.0.1:8000/api/health >/dev/null; then
    echo "STOP: Previous release did not become healthy."
    sudo journalctl -u priceunmask.service -n 50 --no-pager
    exit 1
fi

echo "Previous release restored and API is healthy."
```

Restart the collector only after confirming that the API is healthy and GitHub Actions collection remains disabled. Do not start a second collector process.

## 6. Preserve the existing environment file

For an existing installation, preserve `/etc/priceunmask/priceunmask.env`. Do not recreate, truncate, or overwrite it during deployment.

Verify that the environment file exists, has the expected ownership and permissions, and is readable by the application service account:

```bash
sudo test -s /etc/priceunmask/priceunmask.env
sudo stat -c '%U:%G %a %n' /etc/priceunmask/priceunmask.env
sudo -u priceunmask test -r /etc/priceunmask/priceunmask.env
```

Verify that the existing database configuration points to the shared database without displaying other environment variables:

```bash
sudo grep '^DATABASE_URL=' /etc/priceunmask/priceunmask.env
```

Expected database URL:

```text
DATABASE_URL=sqlite:////opt/priceunmask/shared/data/priceunmask.db
```

If the environment file is missing, empty, unreadable, or points to an unexpected database, stop and investigate before proceeding. Do not overwrite an existing environment file to resolve the problem.

For a genuinely new installation only, create and configure the environment file using the deployment-specific values. Never replace an existing environment file without first backing it up and reviewing its contents.

Do not commit this environment file or put secrets in the repository.

## 7. Install and start the API service

Install the API and collector service definitions from the selected release, not from the repository working directory:

```bash
sudo install -o root -g root -m 644 \
    "$APP_ROOT/current/deploy/systemd/priceunmask.service" \
    /etc/systemd/system/priceunmask.service

sudo install -o root -g root -m 644 \
    "$APP_ROOT/current/deploy/systemd/priceunmask-collector.service" \
    /etc/systemd/system/priceunmask-collector.service
```

Reload systemd and verify the service definitions:

```bash
sudo systemctl daemon-reload

sudo systemd-analyze verify \
    /etc/systemd/system/priceunmask.service \
    /etc/systemd/system/priceunmask-collector.service
```

Enable and start the API only:

```bash
sudo systemctl enable priceunmask.service
sudo systemctl restart priceunmask.service

HEALTHY=0

for attempt in $(seq 1 30); do
    if curl --fail --silent --max-time 5 \
        http://127.0.0.1:8000/api/health >/dev/null; then
        echo "API is healthy."
        HEALTHY=1
        break
    fi

    echo "Waiting for API ($attempt/30)..."
    sleep 2
done

if [ "$HEALTHY" -eq 1 ]; then
    sudo systemctl status priceunmask.service --no-pager
else
    echo "STOP: API did not become healthy within 60 seconds."
    sudo journalctl -u priceunmask.service -n 50 --no-pager
    echo "Do not continue with deployment or start the collector."
    exit 1
fi
```
### Verify automatic restart after a crash

`Restart=on-failure` restarts the API only after an unclean exit. A plain `kill` sends SIGTERM, which is a clean shutdown, so systemd does not restart it. Use SIGKILL to simulate a crash.

Save this block into `/tmp/priceunmask-restart-test.sh` and run it with `bash /tmp/priceunmask-restart-test.sh`:

```bash
set -euo pipefail

OLD_PID="$(systemctl show -p MainPID --value priceunmask.service)"
OLD_RESTARTS="$(systemctl show -p NRestarts --value priceunmask.service)"
echo "Before: PID=$OLD_PID NRestarts=$OLD_RESTARTS"

sudo kill -9 "$OLD_PID"

# RestartSec=5, so give systemd time to start a new process.
NEW_PID="$OLD_PID"
for attempt in $(seq 1 30); do
    NEW_PID="$(systemctl show -p MainPID --value priceunmask.service)"
    if [ "$NEW_PID" != "0" ] && [ "$NEW_PID" != "$OLD_PID" ]; then
        break
    fi
    sleep 1
done

NEW_RESTARTS="$(systemctl show -p NRestarts --value priceunmask.service)"
echo "After:  PID=$NEW_PID NRestarts=$NEW_RESTARTS"

if [ "$NEW_PID" = "0" ] || [ "$NEW_PID" = "$OLD_PID" ]; then
    echo "STOP: systemd did not restart the API."
    exit 1
fi

for attempt in $(seq 1 30); do
    if curl --fail --silent --max-time 5 http://127.0.0.1:8000/api/health; then
        echo
        echo "API restarted and is healthy."
        exit 0
    fi
    sleep 2
done

echo "STOP: API restarted but the health check failed."
exit 1
```

The output must show a new PID, `NRestarts` one higher than before, and `API restarted and is healthy.`

## 8. Configure the Nginx reverse proxy

The Nginx configuration is stored in the selected release:

`/opt/priceunmask/current/deploy/nginx/priceunmask.conf`

Install it:

```bash
sudo install -o root -g root -m 644 \
    "$APP_ROOT/current/deploy/nginx/priceunmask.conf" \
    /etc/nginx/sites-available/priceunmask
```

Enable the PriceUnmask site:

```bash
sudo ln -sfnT \
    /etc/nginx/sites-available/priceunmask \
    /etc/nginx/sites-enabled/priceunmask
```

Check the enabled sites:

```bash
ls -l /etc/nginx/sites-enabled/
```

Inspect any existing default site or other server blocks that may conflict with the PriceUnmask configuration. Do not remove an existing site without confirming it is safe to disable.

Validate the configuration before reloading Nginx:

```bash
sudo nginx -t
```

If validation succeeds, enable and start Nginx:

```bash
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

Check Nginx:

```bash
sudo systemctl is-active nginx
```

## 9. Collector execution decision

The GitHub Actions database is kept in the Actions cache (`data/priceunmask.db` in `collector.yml`). It is not directly downloadable as an artifact. If no existing host database is migrated, the host starts with an empty database and the collector fills it every 4 hours. Data collected by Actions before the switch stays in the old cache and is not moved. If that history is needed, add an `actions/upload-artifact` step for `data/priceunmask.db` to `collector.yml`, run the workflow once, download the file with `gh run download`, and restore it with Section 13.

GitHub Actions and the host collector must never collect simultaneously. Running both can cause overlapping scrape jobs and duplicate collection activity.

Before starting the host collector:

1. Disable the GitHub Actions collector workflow.
2. Confirm that no GitHub Actions collector run is currently in progress.
3. Confirm that the host collector is not already running.
4. Confirm that the API is healthy.

To disable the GitHub Actions workflow:

1. Open the repository on GitHub.
2. Select **Actions**.
3. Select the **Collector** workflow.
4. Open the workflow's three-dot menu and select **Disable workflow**.
5. Return to the Collector workflow runs page.
6. Confirm that no run is queued or in progress.

Do not start the host collector until the workflow is disabled and all existing runs have finished.

Check the host collector and API before starting it:

```bash
if sudo systemctl is-active --quiet priceunmask-collector.service; then
    echo "STOP: Host collector is already running. Do not start another collector."
else
    HEALTHY=0

    for attempt in $(seq 1 30); do
        if curl --fail --silent --max-time 5 \
            http://127.0.0.1:8000/api/health >/dev/null; then
            echo "API is healthy."
            HEALTHY=1
            break
        fi

        echo "Waiting for API ($attempt/30)..."
        sleep 2
    done

    if [ "$HEALTHY" -eq 1 ]; then
        sudo systemctl start priceunmask-collector.service
        sudo systemctl status priceunmask-collector.service --no-pager
    else
        echo "STOP: API did not become healthy within 60 seconds."
        echo "Do not start the collector."
    fi
fi
```

The collector starts scraping when the service starts. Avoid restarting it unnecessarily.

## 10. Health checks

Check the API directly:

```bash
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8000/api/health
```

Check the API through Nginx:

```bash
curl --fail --silent --show-error --max-time 5 http://127.0.0.1/api/health
```

Check collector history through the API:

```bash
curl --fail --silent --show-error --max-time 5 http://127.0.0.1/api/scrape-runs
```

Check database integrity:

```bash
sudo -u priceunmask sqlite3 \
    /opt/priceunmask/shared/data/priceunmask.db \
    'PRAGMA integrity_check;'
```

Expected integrity result:

```text
ok
```

Check service status:

```bash
sudo systemctl is-active priceunmask.service
sudo systemctl is-active priceunmask-collector.service
sudo systemctl is-active nginx
```

## 11. Logs and service recovery

View API logs:

```bash
sudo journalctl -u priceunmask.service -n 100 --no-pager
```

View collector logs:

```bash
sudo journalctl -u priceunmask-collector.service -n 100 --no-pager
```

View Nginx logs:

```bash
sudo journalctl -u nginx.service -n 100 --no-pager
```

Restart the API when required:

```bash
sudo systemctl restart priceunmask.service
```

Restart the collector only after confirming GitHub Actions collection is disabled and no workflow run is in progress:

```bash
sudo systemctl restart priceunmask-collector.service
```

Check whether services are active:

```bash
sudo systemctl is-active priceunmask.service
sudo systemctl is-active priceunmask-collector.service
sudo systemctl is-active nginx
```

## 12. SQLite backup

**Important:** Do not paste the backup commands directly into an interactive Bash shell. The integrity check uses `exit 1`. Until a dedicated backup script is provided, place the commands in this section, in order, into a temporary script such as `/tmp/priceunmask-backup.sh` and run it using `bash /tmp/priceunmask-backup.sh`. This ensures a failed check stops the script without closing your original terminal.

Create the backup directory if it does not already exist:

```bash
set -euo pipefail

sudo install -d -o priceunmask -g priceunmask -m 750 \
    /opt/priceunmask/backups
```

Use SQLite's online backup command rather than copying a live database file. Run the backup as the application service account:

```bash
BACKUP="/opt/priceunmask/backups/priceunmask-$(date -u +%Y%m%d-%H%M%S).db"

sudo -u priceunmask sqlite3 \
    /opt/priceunmask/shared/data/priceunmask.db \
    ".backup '$BACKUP'"
```

Verify the backup file exists:

```bash
sudo test -s "$BACKUP"
sudo ls -lh "$BACKUP"
```

Verify the backup integrity:

```bash
BACKUP_INTEGRITY="$(sudo -u priceunmask sqlite3 "$BACKUP" 'PRAGMA integrity_check;')"

echo "$BACKUP_INTEGRITY"

if [ "$BACKUP_INTEGRITY" != "ok" ]; then
    echo "STOP: Backup integrity check failed."
    exit 1
fi
```

Expected result:

```text
ok
```

Do not manually delete or copy SQLite `-wal` or `-shm` files while the database is active.

## 13. Restore a database backup

**Important:** Do not paste the restore commands directly into an interactive Bash shell. First list the available backups and select the backup you intend to restore. Then place the remaining commands in this section, starting with the `set -euo pipefail` line of the next block, in order, into a temporary script such as `/tmp/priceunmask-restore.sh`. Replace the backup filename before running it using `bash /tmp/priceunmask-restore.sh`.

**Warning:** Restoring a backup replaces the active database and causes temporary downtime. Only perform this procedure when necessary.

**Before starting:** Disable the GitHub Actions collector workflow and confirm that no collector workflow run is in progress. Keep the workflow disabled throughout the restore. Review the selected backup path and verify all preconditions before running the script. A failed check must stop the procedure; do not skip it or continue manually.

List available backups:

```bash
sudo ls -lh /opt/priceunmask/backups/
```

Set the path to the verified backup:

```bash
set -euo pipefail

BACKUP_FILE="/opt/priceunmask/backups/REPLACE_WITH_BACKUP_FILENAME.db"

if ! sudo test -s "$BACKUP_FILE"; then
    echo "STOP: Backup file does not exist or is empty. Do not continue."
    exit 1
fi
```

Verify the selected backup:

```bash
BACKUP_INTEGRITY="$(sudo -u priceunmask sqlite3 "$BACKUP_FILE" 'PRAGMA integrity_check;')"

echo "$BACKUP_INTEGRITY"

if [ "$BACKUP_INTEGRITY" != "ok" ]; then
    echo "STOP: Backup integrity check failed. Do not restore it."
    exit 1
fi
```

Check that both application services are installed:

```bash
API_LOAD="$(sudo systemctl show priceunmask.service -p LoadState --value)"
COLLECTOR_LOAD="$(sudo systemctl show priceunmask-collector.service -p LoadState --value)"

if [ "$API_LOAD" != "loaded" ] || [ "$COLLECTOR_LOAD" != "loaded" ]; then
    echo "STOP: One or more application services are not loaded."
    exit 1
fi
```

Stop both application services:

```bash
sudo systemctl stop priceunmask-collector.service
sudo systemctl stop priceunmask.service
```

Confirm both application services have stopped:

```bash
if sudo systemctl is-active --quiet priceunmask.service || \
   sudo systemctl is-active --quiet priceunmask-collector.service; then
    echo "STOP: One or more application services are still running."
    exit 1
fi

echo "Both application services are stopped."
```

Preserve the current database before restoring:

```bash
PRE_RESTORE="/opt/priceunmask/backups/pre-restore-$(date -u +%Y%m%d-%H%M%S).db"

sudo -u priceunmask sqlite3 \
    /opt/priceunmask/shared/data/priceunmask.db \
    ".backup '$PRE_RESTORE'"
```

Verify the pre-restore backup:

```bash
PRE_RESTORE_INTEGRITY="$(sudo -u priceunmask sqlite3 "$PRE_RESTORE" 'PRAGMA integrity_check;')"

echo "$PRE_RESTORE_INTEGRITY"

if [ "$PRE_RESTORE_INTEGRITY" != "ok" ]; then
    echo "STOP: Pre-restore backup integrity check failed."
    exit 1
fi
```

Restore the verified backup:

```bash
sudo -u priceunmask sqlite3 \
    /opt/priceunmask/shared/data/priceunmask.db \
    ".restore '$BACKUP_FILE'"
```

Verify the restored database:

```bash
RESTORE_INTEGRITY="$(sudo -u priceunmask sqlite3 \
    /opt/priceunmask/shared/data/priceunmask.db \
    'PRAGMA integrity_check;')"

echo "$RESTORE_INTEGRITY"

if [ "$RESTORE_INTEGRITY" != "ok" ]; then
    echo "STOP: Restored database integrity check failed. Do not start the services."
    exit 1
fi
```

Start the API:

```bash
sudo systemctl start priceunmask.service

if ! sudo systemctl is-active --quiet priceunmask.service; then
    echo "STOP: API service failed to start."
    sudo journalctl -u priceunmask.service -n 50 --no-pager
    exit 1
fi
```

Verify API health:

```bash
# Wait up to 60 seconds for the API to become healthy.
HEALTHY=0

for attempt in $(seq 1 30); do
    if curl --fail --silent --max-time 5 \
        http://127.0.0.1:8000/api/health >/dev/null; then
        echo "API is healthy."
        HEALTHY=1
        break
    fi

    echo "Waiting for API ($attempt/30)..."
    sleep 2
done

if [ "$HEALTHY" -ne 1 ]; then
    echo "STOP: API did not become healthy within 60 seconds."
    sudo journalctl -u priceunmask.service -n 50 --no-pager
    exit 1
fi
```

Leave the collector stopped after the database restore.

Before restarting it, repeat the checks in Section 9: confirm that the GitHub Actions collector workflow is disabled, no workflow run is in progress, and host collection is intended. Only then start the host collector:

```bash
sudo systemctl start priceunmask-collector.service
sudo systemctl status priceunmask-collector.service --no-pager
```

If you cannot verify that GitHub Actions collection is disabled and idle, leave the host collector stopped.

**Note:** A full restore drill has not yet been performed. Do not describe this procedure as tested until it has been safely exercised.

## 14. Application rollback

**Deferred:** A safe, tested application rollback procedure is out of scope for this PR and will be implemented in a follow-up PR together with `deploy.sh`.

**Do not use this section to roll back the existing release on the VM.**

The release-based layout may retain previous application versions under `/opt/priceunmask/releases`. However, keeping them does not establish that a rollback is safe.

The follow-up implementation must address:

- Release directory ownership and permissions.
- Safe detection of the previous release from the current symbolic link.
- API service restart and health verification, including a bounded startup wait.
- Compatibility between the previous application version and the current shared database.
- Failure handling that does not leave the application pointing to an invalid release.

No application rollback test is claimed for this PR. A rollback procedure must be implemented and safely tested before it is used to replace or restore the existing release on the VM.

## 15. Deployment limitations

- Tested on Ubuntu 24.04 under WSL2, not on a public VPS.
- WSL2 services depend on the local Windows machine and WSL instance being available.
- No public-domain, TLS, firewall, or external VPS deployment test has been completed.
- `deploy/deploy.sh` is not yet available in this working tree; its automated deployment flow remains untested and is deferred to a follow-up PR.
- Backup creation and integrity verification were tested. A full restore drill remains to be performed.
- Application rollback is deferred to a follow-up PR and has not been implemented or tested.
- The runbook describes the intended release-based deployment procedure. Do not treat every documented step as tested merely because the API and collector were previously run successfully on WSL2.
