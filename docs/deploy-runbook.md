# PriceUnmask Linux VM Deployment Runbook

## 1. Purpose and scope

This runbook documents the deployment of PriceUnmask on an Ubuntu 24.04 WSL2 Linux VM.

This is a local deployment-readiness test, not a real VPS or public production deployment. Services are managed with systemd, and Nginx acts as a reverse proxy.

## 2. Architecture

- FastAPI application: `priceunmask-api.service`
- Background collector: `priceunmask-collector.service`
- Reverse proxy: Nginx
- Database: SQLite
- Persistent database location: `/opt/priceunmask/shared/data/priceunmask.db`
- Environment file: `/etc/priceunmask/priceunmask.env`
- Application directory: `/opt/priceunmask/current`
- Python virtual environment: `/opt/priceunmask/venv`

The API and collector run as separate systemd services. Both use the same environment file and database.

## 3. Required Ubuntu packages

Install the required packages:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-full nginx sqlite3 rsync curl
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

Create the application, persistent data, backup, and configuration directories:

```bash
sudo mkdir -p /opt/priceunmask/current
sudo mkdir -p /opt/priceunmask/shared/data
sudo mkdir -p /opt/priceunmask/backups
sudo mkdir -p /etc/priceunmask

sudo chown -R priceunmask:priceunmask /opt/priceunmask
```

## 5. Copy the application and install Python dependencies

The following example assumes the repository is available at:

`/mnt/c/Users/venky/priceunmask-release-check`

Adjust the source path if the repository is stored elsewhere.

Stage a copy without Git metadata, local virtual environments, secrets, or local database files:

```bash
mkdir -p /tmp/priceunmask-copy

rsync -av \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='.env' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='data/*.db' \
  --exclude='*.sqlite*' \
  /mnt/c/Users/venky/priceunmask-release-check/ \
  /tmp/priceunmask-copy/
```

Copy the application into its installation directory:

```bash
sudo rsync -av /tmp/priceunmask-copy/ /opt/priceunmask/current/

sudo chown -R priceunmask:priceunmask /opt/priceunmask
sudo find /opt/priceunmask -type d -exec chmod 755 {} \;
sudo find /opt/priceunmask -type f -exec chmod 644 {} \;
```

Create the Python virtual environment:

```bash
sudo -u priceunmask python3 -m venv /opt/priceunmask/venv
```

Install the application dependencies:

```bash
sudo -u priceunmask /opt/priceunmask/venv/bin/pip install --upgrade pip

sudo -u priceunmask /opt/priceunmask/venv/bin/pip install -r /opt/priceunmask/current/requirements.txt
```

Verify the installed dependencies:

```bash
sudo -u priceunmask /opt/priceunmask/venv/bin/pip check
```

Expected output:

```text
No broken requirements found.
```

## 6. Configure the environment file

Create the environment file:

```bash
sudo install -o root -g priceunmask -m 640 /dev/null /etc/priceunmask/priceunmask.env
sudoedit /etc/priceunmask/priceunmask.env
```

Add the following configuration. Replace `YOUR_CONTACT_EMAIL` with a valid contact address.

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
```

Do not commit this environment file or put secrets in the repository.

## 7. Install and start the systemd services

Install the API and collector service definitions:

```bash
sudo install -o root -g root -m 644 deploy/systemd/priceunmask-api.service /etc/systemd/system/priceunmask-api.service

sudo install -o root -g root -m 644 deploy/systemd/priceunmask-collector.service /etc/systemd/system/priceunmask-collector.service
```

Reload systemd and verify the service definitions:

```bash
sudo systemctl daemon-reload

sudo systemd-analyze verify \
  /etc/systemd/system/priceunmask-api.service \
  /etc/systemd/system/priceunmask-collector.service
```

Enable and start both services:

```bash
sudo systemctl enable --now priceunmask-api.service
sudo systemctl enable --now priceunmask-collector.service
```

Check their status:

```bash
sudo systemctl status priceunmask-api.service --no-pager
sudo systemctl status priceunmask-collector.service --no-pager
```

The collector starts its scraping process when the service starts. Avoid restarting it unnecessarily.

## 8. Nginx reverse proxy

The Nginx configuration is stored in:

`deploy/nginx/priceunmask.conf`

Install and enable it:

```bash
sudo install -o root -g root -m 644 deploy/nginx/priceunmask.conf /etc/nginx/sites-available/priceunmask

sudo ln -sfn /etc/nginx/sites-available/priceunmask /etc/nginx/sites-enabled/priceunmask
```

If the default Nginx site conflicts with the PriceUnmask server block, disable its enabled symlink:

```bash
sudo unlink /etc/nginx/sites-enabled/default
```

Validate and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Health checks

Check the API directly:

```bash
curl -i http://127.0.0.1:8000/api/health
```

Check through Nginx:

```bash
curl -i http://127.0.0.1/api/health
```

Check collector history through the API:

```bash
curl -i http://127.0.0.1/api/scrape-runs
```

Check database integrity:

```bash
sqlite3 /opt/priceunmask/shared/data/priceunmask.db 'PRAGMA integrity_check;'
```

Expected integrity result:

```text
ok
```

## 10. Logs and service recovery

View API logs:

```bash
sudo journalctl -u priceunmask-api.service -n 100 --no-pager
```

View collector logs:

```bash
sudo journalctl -u priceunmask-collector.service -n 100 --no-pager
```

Restart services when required:

```bash
sudo systemctl restart priceunmask-api.service
sudo systemctl restart priceunmask-collector.service
```

Check whether services are active:

```bash
sudo systemctl is-active priceunmask-api.service
sudo systemctl is-active priceunmask-collector.service
sudo systemctl is-active nginx
```

## 11. SQLite backup

Create the backup directory:

```bash
sudo mkdir -p /opt/priceunmask/backups
sudo chown root:priceunmask /opt/priceunmask/backups
sudo chmod 750 /opt/priceunmask/backups
```

Use SQLite's online backup command rather than copying a live database file:

```bash
BACKUP="/opt/priceunmask/backups/priceunmask-$(date -u +%Y%m%d-%H%M%S).db"

sudo sqlite3 /opt/priceunmask/shared/data/priceunmask.db ".backup '$BACKUP'"

sudo chown root:priceunmask "$BACKUP"
sudo chmod 640 "$BACKUP"
```

Verify the backup:

```bash
sudo sqlite3 "$BACKUP" 'PRAGMA integrity_check;'
```

Expected result:

```text
ok
```
## 12. Restore a database backup

**Warning:** Restoring a backup replaces the active database. Confirm the backup file before proceeding. This procedure causes temporary downtime.

List available backups:

```bash
sudo ls -lh /opt/priceunmask/backups/
```

Set the path to the verified backup:

```bash
BACKUP_FILE="/opt/priceunmask/backups/REPLACE_WITH_BACKUP_FILENAME.db"

sudo test -f "$BACKUP_FILE" || {
    echo "Backup file not found"
    exit 1
}
```

Stop both application services:

```bash
sudo systemctl stop priceunmask-collector.service
sudo systemctl stop priceunmask-api.service

if sudo systemctl is-active --quiet priceunmask-collector.service; then
    echo "Collector is still running. Aborting restore."
    exit 1
fi

if sudo systemctl is-active --quiet priceunmask-api.service; then
    echo "API is still running. Aborting restore."
    exit 1
fi

echo "Both application services are stopped."
```

Preserve the current database using a unique timestamped filename:

```bash
PRE_RESTORE="/opt/priceunmask/backups/pre-restore-$(date -u +%Y%m%d-%H%M%S).db"

sudo sqlite3 /opt/priceunmask/shared/data/priceunmask.db ".backup '$PRE_RESTORE'"

sudo chown root:priceunmask "$PRE_RESTORE"
sudo chmod 640 "$PRE_RESTORE"
```

Replace the active database:

```bash
sudo rm -f /opt/priceunmask/shared/data/priceunmask.db-wal
sudo rm -f /opt/priceunmask/shared/data/priceunmask.db-shm

sudo install -o priceunmask -g priceunmask -m 640 \
  "$BACKUP_FILE" \
  /opt/priceunmask/shared/data/priceunmask.db
```

Check database integrity:

```bash
sudo -u priceunmask sqlite3 /opt/priceunmask/shared/data/priceunmask.db 'PRAGMA integrity_check;'
```

Expected result:

```text
ok
```

Start the API and collector:

```bash
sudo systemctl start priceunmask-api.service
sudo systemctl start priceunmask-collector.service
```

Verify the API:

```bash
curl -i http://127.0.0.1/api/health
```
**Note:** A full restore drill has not yet been performed. Do not describe this procedure as tested until it has been safely exercised.

## 13. Application rollback

The current VM setup uses `/opt/priceunmask/current` as a direct application directory. It does not yet use versioned release directories or a `current` symlink.

Therefore, an atomic release-symlink rollback has not been implemented or tested.

Before replacing application code in a future deployment, preserve the previous application version and keep the persistent database outside the application directory.

A proper release rollback should restore the previous application version, retain the shared database, restart both services, and verify the health endpoint.

Do not claim an automated rollback until the release deployment script implements and tests it.

## 14. Deployment limitations

- Tested on Ubuntu 24.04 under WSL2, not on a public VPS.
- WSL2 services depend on the local Windows machine and WSL instance being available.
- No public-domain, TLS, firewall, or external VPS deployment test has been completed.
- `deploy/deploy.sh` is not yet available in this working tree; its automated deployment flow remains untested.
- Backup creation and integrity verification were tested. A full restore drill remains to be performed.
- Application rollback using versioned releases remains to be implemented and tested.
