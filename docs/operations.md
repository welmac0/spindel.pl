# Operations and deployment

## Production layout

Spindel runs on a single Ubuntu VPS at Hetzner. [Production Compose](../docker/compose.prod.yaml) defines the backend, frontend/Nginx, and Certbot. Nginx publishes ports 80/443; the backend has no published port. SQLite is stored in the external volume `docker_wymiana_data`.

The existing deployment checkout is expected at `/opt/wymiana-zajec`. Paths in the scripts and service units describe this layout, not a generic installer. Provisioning a new host also requires DNS, certificates, an external database volume, secrets, host access controls, and systemd units. Do not assume a production Compose start alone provisions these prerequisites.

Keep runtime credentials outside Git. The repository template documents variable names, not production values. Live host and GitHub settings must be verified separately from this guide.

## Deployment workflow

The manually triggered [Deploy production workflow](../.github/workflows/deploy.yml):

1. Checks CI for the current `main` revision.
2. Connects to the VPS with SSH using a deployment key and pinned known-hosts data.
3. Updates the production checkout to `main`.
4. Starts the SQLite backup service before rebuilding.
5. Builds and starts backend/frontend containers.
6. Waits for container health checks and checks the public API and Nginx health URLs.

Required GitHub secret names are `VPS_SSH_PRIVATE_KEY`, `VPS_KNOWN_HOSTS`, `VPS_HOST`, and `VPS_USER`. Prefer the `production` environment for deployment credentials; restrict its branches to `main` and configure approval rules where supported. The workflow's environment reference does not itself enable these settings.

The workflow deploys `main`, not an immutable release tag, and the checkout is updated after the CI lookup. Avoid concurrent changes to `main` during deployment. A tag labels a revision; it does not trigger this deployment. Record the revision actually deployed and verified.

### Post-deployment checks

- Confirm backend/frontend report `healthy`.
- Check [API health](https://spindel.pl/api/health) and [Nginx health](https://spindel.pl/nginx-health).
- Inspect backend/frontend/Certbot logs locally without publishing secrets or user data.
- Verify backup and monitoring timers.
- Run a small [smoke test](testing.md#after-deployment) with controlled accounts.

Do not remove the database volume or use volume-deleting cleanup as a deployment step. A failed deployment does not trigger automatic rollback.

## Backups and recovery

[The backup script](../scripts/backup_sqlite.sh) is invoked by the [backup service](../deployment/systemd/wymiana-zajec-backup.service) and [timer](../deployment/systemd/wymiana-zajec-backup.timer).

- The timer is configured to back up every six hours.
- The default destination is `/opt/wymiana-zajec/backups/`, outside the application volume.
- Backups use SQLite's backup mechanism and are checked with `PRAGMA integrity_check`.
- SHA-256 checksum files accompany completed backups.
- Default retention is the 14 most recent copies.

An additional copy should be stored off-host. The existing [Mac backup notes](notes-how2/mac_backup.md) describe a workstation-specific SSH/rsync setup in Polish.

Periodically restore a backup into an isolated location, verify its checksum and integrity, and test application access against that restored copy. Never point restore experiments at production storage. During a real restore, stop writers, preserve the current database, confirm file ownership and schema compatibility, then verify health and core flows before reopening access.

Backup success and website availability are separate signals. The external HTTP monitor does not verify backup age or integrity; automated backup-failure alerting is separate work.

## Monitoring

### Container health

Compose checks backend application/database health and frontend HTTP availability. Container health is an observation, not a complete end-to-end user journey or proof of automatic recovery.

### Host-side monitor

[The host monitor](../scripts/check_health_inner.sh) inspects the backend container's Docker health status; it does not need a publicly exposed backend port. Its [service](../deployment/systemd/wymiana-zajec-healthcheck-inner.service) and [timer](../deployment/systemd/wymiana-zajec-healthcheck-inner.timer) run on the VPS. It sends Brevo notifications on state changes.

Because it shares the application's host, it cannot independently report a complete VPS or network outage.

### External monitor

[The external monitor](../scripts/check_external_health.sh) runs on a separate always-on Linux machine, such as a Raspberry Pi. It checks the public API and Nginx health endpoints over HTTPS. The default threshold is two consecutive failures; it sends an alert on failure and another when both endpoints recover. It does not need SSH access to production or inbound access to the monitor's home network.

To install it, copy the script and the checked-in [service](../deployment/systemd/spindel-external-monitor.service) and [timer](../deployment/systemd/spindel-external-monitor.timer) to the external host. The service expects:

| Item | Expected location/value |
| --- | --- |
| Script | `/usr/local/sbin/spindel-external-monitor.sh` |
| Service and timer | `/etc/systemd/system/` |
| System user/group | `spindel-monitor` |
| Credentials file | `/etc/spindel-monitor/monitor.env` |
| State directory | `/var/lib/spindel-external-monitor/` (managed by systemd) |
| Dependencies | Bash, curl, Python 3 |

Create the credentials file locally on that host with `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`, and `ALERT_EMAIL`; `FAILURE_THRESHOLD=2` is optional. Never copy real credentials into this repository. Use a root-owned file with restrictive permissions readable by the service setup, then reload systemd and enable the timer. Do not overwrite credentials when updating the script or units.

Test alerts using a temporary monitor-local URL override to a nonexistent path rather than stopping production. Restore the correct URL and verify recovery. The script's comments list supported overrides. The automated [monitor tests](../tests/test_external_monitor.sh) validate transitions without sending real email.

The external monitor depends on its own power, network, and Brevo connectivity. If it cannot reach the internet, it cannot send an alert; independent monitoring infrastructure would reduce that risk.

## Maintenance mode

`VITE_MAINTENANCE` is a frontend build-time flag. Change it in the build environment and rebuild/recreate the frontend to show or remove the maintenance page. Restarting an unchanged frontend image does not change the flag. See the existing [maintenance notes](notes-how2/maintenance_mode.md) for the deployment-specific procedure.

This hides the UI, not the API. It is not a substitute for stopping database writers during a restore or incompatible schema change.

## Rollback

Keep the last verified revision/image and a valid pre-deployment backup available. The current workflow has no automatic rollback or tag-selecting deploy option.

If a deployment fails, stop further deployments, use maintenance mode where helpful, restore known-good code/images without deleting the volume, and verify health plus a smoke test. Assess database compatibility separately before restoring data: rolling back code must not automatically overwrite the database or discard new user changes.

## Development workflow

Solo maintainer commits directly to `main` are supported; branches and pull requests are useful for risky changes and external contributions. Run relevant tests and ensure CI succeeds before deployment. Keep environment approvals, branch rules, and SSH/firewall access consistent with this workflow. See [contributing](../CONTRIBUTING.md) and [security](security.md).