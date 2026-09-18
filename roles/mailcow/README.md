# role: mailcow (appliance)

mailcow-dockerized **2026-05c** on `vm-mailcow-01` (DMZ `10.1.2.120`, 18 containers). MX for the platform domain; **only port 25 forwarded from WAN** — client ports are VPN/internal, webmail (SOGo, Authentik SSO) via Traefik `mail.<domain>`. DKIM/SPF `-all`/DMARC `p=reject`; outbound DANE via Telenet PBR.

- Managed via the mailcow **API only** (`fabric/mailcow.json` api_key); per-service mailboxes come from the `mailbox` concern-role + `playbooks/mailboxes.yml`.
- `disable_plaintext_auth=yes`; `recipient_delimiter=+` (plus-addressing platform-wide).
- Its own MariaDB stays bundled (appliance) — not the shared DB.
- Upgrade = bump `mailcow_git_version` deliberately (read the release notes).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/mailcow.yml`

## Backup & restore

Class **B**: `mailcow-backup.timer` 01:00 runs the official helper (vmail+mysql+redis+conf) → `/var/backups/mailcow` → PBS 01:30; the control node runs `--tags backup` nightly at 03:30 (cron) → archive → SeaweedFS `mailcow-backups` (key in Vault `prod/mailcow/s3`) → Contabo replica; local and S3 copies pruned after `mailcow_backup_retention_days`. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `docker compose ps` in `/opt/mailcow-dockerized`; SMTP auth test on 587 (never `doveadm auth test` — it doesn't work against mailcow's passdb).
- Restart: `docker compose up -d` (force-recreate only for image/driver changes).
- Common: 502s from the S3 backup job → SeaweedFS memory/health; mail from a DMZ host to `mail.<domain>` → hairpin, use the asset FQDN `vm-mailcow-01.<domain>`.
