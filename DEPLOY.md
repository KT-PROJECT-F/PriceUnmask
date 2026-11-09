# Production Deployment - #244

## Host
See Hemalatha's PR for host selection - Part of #244

## Process Supervisor
systemd service 'deploy/priceunmask.service'
Restart=always - restarts automatically within 5 seconds if app crashes

## Collector
GitHub Actions 'collector.yml' hourly cron continues on host.
No laptop needed.

## Rollback
If deploy fails:
1. Go to Render Dashboard -> Deploys
2. Click previous successful deploy -> Rollback
3. Or: git revert <commit> and push to dev