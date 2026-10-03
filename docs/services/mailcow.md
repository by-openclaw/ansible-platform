# mailcow — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: mailcow`). Role `roles/mailcow`, play `playbooks/mailcow.yml`, guest `vm-mailcow-01` (the one VM-based service: mailcow's stack is managed as a whole). Audit: [`docs/audits/mailcow-2026-10-02.md`](../audits/mailcow-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` (native OIDC), `services/0002-email-infrastructure` (mail flow, per-tool mailboxes).
2. **Authentik application:** OIDC, slug `mailcow` (`group_vars/all/sso.yml`); mailcow's Generic-OIDC auth source; first login auto-provisions the mailbox from the `mailcow_template` claim.
3. **Access model:** IdP-enforced — `mailcow-users` may log in (`restrict_to_group`); service mailboxes (`<service>@<domain>`) are provisioned by `roles/mailbox` through each service's scaffold, with the admin delegate; the Nextcloud Mail app uses the Dovecot master user.
4. **Vault paths:** `secret/{env}/mailcow/{api, oidc, master-user, s3}` (admin API key, OIDC client minted by `roles/authentik`, Dovecot master user, the backup bucket's scoped key), `secret/{env}/mail/<service>` per service mailbox, the Cloudflare token for the lego wildcard.
5. **Ansible adapter + vars:** `roles/mailcow` (clone at the pinned release tag, `mailcow.conf` rendered by the role, compose override for pins, API configuration of domains/templates/OIDC/postmaster, wildcard cert via lego, backups), `roles/mailbox` for every service mailbox.
6. **Removal notes:** mailboxes are suspended/exported before deletion (`roles/mailbox`, S3 export); the service itself: `playbooks/decommission-service.yml`.

## Notifications (services/0005)

1. **Transport:** mailcow IS the platform's mail transport (`services/0002`): every service submits as its own mailbox on `:587` STARTTLS; outbound delivered directly (standalone mode).
2. **What is sent:** watchdog notices to `postmaster@<domain>`; quota/alias mails to users; DMARC reports arrive at `postmaster@`.
3. **Alerting path:** Prometheus blackbox (HTTPS `:8443`, SMTP STARTTLS `:25`/`:587`, IMAPS `:993`) → Alertmanager → Discord/mail; host node metrics; no application metrics (platform note).
4. **Logs:** every container → journald → promtail → Loki (`host="vm-mailcow-01"`, 14 containers emit); CrowdSec agent with the postfix + dovecot collections over the containers' stdout.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B (`docs/backup.md`): mailcow's own app-consistent set daily at 01:00 (`mailcow-backup.timer`: vmail, MariaDB, Redis, conf), archived and pushed to the platform S3 by the same timer (pinned rclone, 7-day retention local + bucket), the whole VM in PBS daily (vmid 102).
