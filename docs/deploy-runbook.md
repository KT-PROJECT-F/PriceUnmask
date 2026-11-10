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
- Previous release record: `/opt/priceunmask/previous-release`
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

The `current` path must be a symbolic link to a directory inside `releases`, not a normal application directory.

If `/opt/priceunmask/current` already exists as a real directory, do not overwrite it. Preserve and migrate the existing installation deliberately before continuing.

**Important:** Run the deployment commands in Sections 5–8 sequentially in the same Bash session.

## 5. Copy the application and install Python dependencies
Set the source repository path. Replace the example with the location of your own repository:

```bash
set -euo pipefail

SOURCE_DIR="/path/to/priceunmask-release-check"
```

Verify the repository before selecting the commit:

```bash
if ! git -C "$SOURCE_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "STOP: SOURCE_DIR is not a Git repository"
    exit 1
fi

COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
if ! git -C "$SOURCE_DIR" cat-file -e "$COMMIT^{commit}"; then
    echo "STOP: Selected commit is invalid."
    exit 1
fi

if ! git -C "$SOURCE_DIR" cat-file -e "$COMMIT:backend"; then
    echo "STOP: Selected commit does not contain backend"
    exit 1
fi

if ! git -C "$SOURCE_DIR" cat-file -e "$COMMIT:requirements.txt"; then
    echo "STOP: Selected commit does not contain requirements.txt"
    exit 1
fi

if ! git -C "$SOURCE_DIR" cat-file -e "$COMMIT:deploy/systemd/priceunmask.service"; then
    echo "STOP: API systemd service file is missing from the selected commit"
    exit 1
fi

if ! git -C "$SOURCE_DIR" cat-file -e "$COMMIT:deploy/systemd/priceunmask-collector.service"; then
    echo "STOP: Collector systemd service file is missing from the selected commit"
    exit 1
fi

if ! git -C "$SOURCE_DIR" cat-file -e "$COMMIT:deploy/nginx/priceunmask.conf"; then
    echo "STOP: Nginx configuration is missing from the selected commit"
    exit 1
fi

echo "Deploying commit: $COMMIT"
# Set the application root and validate the existing release.
APP_ROOT="/opt/priceunmask"
PREVIOUS_RELEASE=""

if [ -e "$APP_ROOT/current" ] && [ ! -L "$APP_ROOT/current" ]; then
    echo "STOP: Existing current path is not a symlink. Migrate it safely first."
    exit 1
fi

if [ -L "$APP_ROOT/current" ]; then
    PREVIOUS_RELEASE="$(readlink -f "$APP_ROOT/current")" || {
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

    if [ ! -d "$PREVIOUS_RELEASE" ]; then
        echo "STOP: Existing current symlink does not point to a valid release."
        exit 1
    fi
fi
```

This procedure deliberately deploys the selected committed revision. Uncommitted working-tree changes are not included.

Create a unique release directory:

```bash

RELEASE_NAME="$(date -u +%Y%m%d-%H%M%S)-$(git -C "$SOURCE_DIR" rev-parse --short "$COMMIT")"
RELEASE_DIR="$APP_ROOT/releases/$RELEASE_NAME"
if [ -e "$RELEASE_DIR" ]; then
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
```bash
# Activate the new release.
if [ -e "$APP_ROOT/current.new" ] || [ -L "$APP_ROOT/current.new" ]; then
    echo "STOP: Temporary current.new path already exists."
    exit 1
fi

sudo ln -s "$RELEASE_DIR" "$APP_ROOT/current.new"

if ! sudo mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"; then
    sudo rm -f "$APP_ROOT/current.new"
    echo "STOP: Release activation failed."
    exit 1
fi

if [ -n "$PREVIOUS_RELEASE" ]; then
    printf '%s\n' "$PREVIOUS_RELEASE" |
        sudo tee "$APP_ROOT/previous-release" >/dev/null
else
    sudo rm -f "$APP_ROOT/previous-release"
fi
```
## 6. Configure the environment file

Create the environment file:

```bash
sudo install -o root -g priceunmask -m 640 /dev/null /etc/priceunmask/priceunmask.env
sudoedit /etc/priceunmask/priceunmask.env
```

Add the following configuration. Replace `YOUR_CONTACT_EMAIL` with a valid contact address:

```dotenv
DATABASE_URL=sqlite:////opt/priceunmask/shared/data/priceunmask.db
SCRAPE_TARGET_URL=https://books.toscrape.com/
SCRAPE_INTERVAL_HOURS=4
SCRAPE_USER_AGENT=PriceUnmaskBot/0.1 (learning project; contact: YOUR_CONTACT_EMAIL)
SCRAPE_DELAY_SECONDS=3
SCRAPE_MAX_PAGES=3
STALE_RUN_MINUTES=30
```

Save the file and verify its permissions:

```bash
sudo chown root:priceunmask /etc/priceunmask/priceunmask.env
sudo chmod 640 /etc/priceunmask/priceunmask.env
sudo test -r /etc/priceunmask/priceunmask.env
```

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
sudo systemctl status priceunmask.service --no-pager
```

Do not start the collector yet. Follow Section 9 first.

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

GitHub Actions and the host collector must never collect simultaneously. Running both can cause overlapping scrape jobs and duplicate collection activity.

Before starting the host collector:

1. Disable the GitHub Actions collector workflow.
2. Confirm that no GitHub Actions collector run is currently in progress.
3. Confirm that the host collector is not already running.
4. Confirm that the API is healthy.

Check the host collector:

```bash
if sudo systemctl is-active --quiet priceunmask-collector.service; then
    echo "STOP: Host collector is already running. Do not start another collector."
    exit 1
fi
```

Only after confirming the GitHub Actions workflow is disabled and no run is in progress, enable and start the host collector:

```bash
if ! curl --fail --silent --show-error \
    http://127.0.0.1:8000/api/health; then
    echo "STOP: API health check failed. Do not start the collector."
    exit 1
fi

sudo systemctl start priceunmask-collector.service
sudo systemctl status priceunmask-collector.service --no-pager
```

The collector starts scraping when the service starts. Avoid restarting it unnecessarily.

## 10. Health checks

Check the API directly:

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/api/health
```

Check the API through Nginx:

```bash
curl -i http://127.0.0.1/api/health
```

Check collector history through the API:

```bash
curl -i http://127.0.0.1/api/scrape-runs
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

Create the backup directory if it does not already exist:

```bash
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

**Warning:** Restoring a backup replaces the active database and causes temporary downtime. Only perform this procedure when necessary.

**Before starting:** Disable the GitHub Actions collector workflow and confirm that no collector workflow run is in progress. Keep the workflow disabled throughout the restore. Do not proceed if you cannot verify this.

List available backups:

```bash
sudo ls -lh /opt/priceunmask/backups/
```

Set the path to the verified backup:

```bash
BACKUP_FILE="/opt/priceunmask/backups/REPLACE_WITH_BACKUP_FILENAME.db"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "STOP: Backup file does not exist. Do not continue."
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
curl --fail --silent --show-error http://127.0.0.1:8000/api/health
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

The release-based layout keeps previous application versions available under `/opt/priceunmask/releases`. The `current` symbolic link identifies the active release.

The deployment procedure records the previous release in:

`/opt/priceunmask/previous-release`

**Warning:** Rollback causes temporary application downtime. It does not restore or replace the shared database. If a database migration or schema change is incompatible with the previous release, application rollback alone may not restore service.

Before rolling back, verify the previous release record:

```bash
PREVIOUS_RELEASE="$(sudo cat /opt/priceunmask/previous-release)" || {
    echo "STOP: Cannot read previous release record."
    exit 1
}

if [ -z "$PREVIOUS_RELEASE" ]; then
    echo "STOP: Previous release record is empty."
    exit 1
fi

PREVIOUS_RELEASE="$(readlink -f -- "$PREVIOUS_RELEASE")" || {
    echo "STOP: Cannot resolve previous release path."
    exit 1
}

case "$PREVIOUS_RELEASE" in
    /opt/priceunmask/releases/*)
        ;;
    *)
        echo "STOP: Previous release resolves outside the releases directory."
        exit 1
        ;;
esac

if [ ! -d "$PREVIOUS_RELEASE" ]; then
    echo "STOP: Previous release directory does not exist."
    exit 1
fi

for FILE in \
    deploy/systemd/priceunmask.service \
    deploy/systemd/priceunmask-collector.service \
    deploy/nginx/priceunmask.conf
do
    if [ ! -f "$PREVIOUS_RELEASE/$FILE" ]; then
        echo "STOP: Required rollback configuration is missing: $FILE"
        exit 1
    fi
done

echo "Previous release: $PREVIOUS_RELEASE"
```

Check whether the collector is running:

```bash
COLLECTOR_WAS_ACTIVE="no"

if sudo systemctl is-active --quiet priceunmask-collector.service; then
    COLLECTOR_WAS_ACTIVE="yes"
fi
```
Record and validate the currently active release:

```bash
CURRENT_RELEASE="$(readlink -f /opt/priceunmask/current)"

case "$CURRENT_RELEASE" in
    /opt/priceunmask/releases/*)
        ;;
    *)
        echo "STOP: Current release path is invalid."
        exit 1
        ;;
esac

if [ ! -d "$CURRENT_RELEASE" ]; then
    echo "STOP: Current release directory does not exist."
    exit 1
fi
if [ "$PREVIOUS_RELEASE" = "$CURRENT_RELEASE" ]; then
    echo "STOP: Previous release is already active."
    exit 1
fi
echo "Current release: $CURRENT_RELEASE"
```

Stop both application services before switching releases:

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


Switch back to the previous release:

```bash
ROLLBACK_LINK="/opt/priceunmask/current.rollback.$$"

if [ -e "$ROLLBACK_LINK" ] || [ -L "$ROLLBACK_LINK" ]; then
    echo "STOP: Temporary rollback link already exists."
    exit 1
fi

sudo ln -s "$PREVIOUS_RELEASE" "$ROLLBACK_LINK"

if ! sudo mv -Tf "$ROLLBACK_LINK" /opt/priceunmask/current; then
    sudo rm -f "$ROLLBACK_LINK"
    echo "STOP: Release switch failed."
    exit 1
fi

if [ "$(readlink -f /opt/priceunmask/current)" != "$PREVIOUS_RELEASE" ]; then
    echo "STOP: Active release verification failed."
    exit 1
fi
```

Restore the systemd service definitions from the previous release:

```bash
sudo install -o root -g root -m 644 \
    "$PREVIOUS_RELEASE/deploy/systemd/priceunmask.service" \
    /etc/systemd/system/priceunmask.service

sudo install -o root -g root -m 644 \
    "$PREVIOUS_RELEASE/deploy/systemd/priceunmask-collector.service" \
    /etc/systemd/system/priceunmask-collector.service

sudo systemctl daemon-reload
```

Restore and validate the Nginx configuration:

Verify that the PriceUnmask Nginx site is enabled:

```bash
if [ ! -L /etc/nginx/sites-enabled/priceunmask ]; then
    echo "STOP: PriceUnmask Nginx site is not enabled."
    exit 1
fi

readlink -f /etc/nginx/sites-enabled/priceunmask
```


```bash
sudo install -o root -g root -m 644 \
    "$PREVIOUS_RELEASE/deploy/nginx/priceunmask.conf" \
    /etc/nginx/sites-available/priceunmask

sudo nginx -t
```

If Nginx validation fails, do not proceed as though rollback is complete. Investigate and correct the configuration first.

Start the API:

```bash
sudo systemctl start priceunmask.service

if ! sudo systemctl is-active --quiet priceunmask.service; then
    echo "STOP: API service is not active."
    sudo journalctl -u priceunmask.service -n 50 --no-pager
    exit 1
fi

sudo systemctl status priceunmask.service --no-pager
```

Verify the active release:

```bash
ACTIVE_RELEASE="$(readlink -f /opt/priceunmask/current)"

if [ "$ACTIVE_RELEASE" != "$PREVIOUS_RELEASE" ]; then
    echo "STOP: Active release does not match the previous release."
    exit 1
fi

echo "Active release verified: $ACTIVE_RELEASE"
```

Verify application health:

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/api/health
```

Do not continue if the API health check fails. Investigate the service and application logs first.

Reload Nginx after the API health check succeeds:

```bash
if ! sudo systemctl reload nginx; then
    echo "STOP: Nginx reload failed."
    exit 1
fi

if ! sudo systemctl is-active --quiet nginx; then
    echo "STOP: Nginx is not active after reload."
    exit 1
fi

sudo systemctl status nginx --no-pager
```

Update the previous-release record only after the API health check and Nginx reload succeed:

```bash
printf '%s\n' "$CURRENT_RELEASE" |
    sudo tee /opt/priceunmask/previous-release >/dev/null
```

If the collector was running before rollback, start it again only after confirming GitHub Actions collection is disabled and no workflow run is in progress:

```bash
if [ "$COLLECTOR_WAS_ACTIVE" = "yes" ]; then
    sudo systemctl start priceunmask-collector.service

    if ! sudo systemctl is-active --quiet priceunmask-collector.service; then
        echo "STOP: Collector service failed to start."
        sudo journalctl -u priceunmask-collector.service -n 50 --no-pager
        exit 1
    fi

    sudo systemctl status priceunmask-collector.service --no-pager
fi

```

The database remains in `/opt/priceunmask/shared/data` and is not replaced during application rollback.

Keep previous releases until the new release has been verified. Do not claim rollback testing is complete until the procedure has been exercised on the Linux VM.

## 15. Deployment limitations

- Tested on Ubuntu 24.04 under WSL2, not on a public VPS.
- WSL2 services depend on the local Windows machine and WSL instance being available.
- No public-domain, TLS, firewall, or external VPS deployment test has been completed.
- `deploy/deploy.sh` is not yet available in this working tree; its automated deployment flow remains untested.
- Backup creation and integrity verification were tested. A full restore drill remains to be performed.
- Application rollback using versioned releases is documented but has not yet been tested on the Linux VM.
- The runbook describes the intended release-based deployment procedure. Do not treat every documented step as tested merely because the API and collector were previously run successfully on WSL2.