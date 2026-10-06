# role: security_audit

Read-only fleet **CVE / update-currency audit** (identity/0008 · security). It **detects**, never patches — remediation is `roles/updates` (staged waves, `playbooks/updates.yml`).

## What it checks (four layers)

| Layer | Tool | Sees |
|---|---|---|
| **OS** | `debsecan` (Debian CVE↔package) + `apt-get -s dist-upgrade` + `/var/run/reboot-required` | host CVEs with a fix available, security-update count, pending reboot |
| **Containers** | **Trivy** (`aquasec/trivy:0.58.1`, cached DB volume) against every **running** image that fits in the host's free space | the real service CVE surface — host apt cannot see inside containers |
| **Appliance** | OPNsense firmware audit (API) — via the opnsense role's firmware check | firewall currency |
| **Report** | consolidated dated JSON → Loki + Discord `#alerts` + optional GitLab issues | one place, tracked over time |

## Flow

1. `playbooks/security-audit.yml` play 1 runs this role on `all:!opnsense:!nodes`: `tasks/os.yml` (debsecan + apt + reboot) and, where Docker runs, `tasks/containers.yml` (Trivy per running image). Each host writes `/var/log/security-audit/<host>.json` and sets `security_audit_host_record`.
2. Play 2 (controller) aggregates every host record → `~/.openclaw/workspace/infra/security-audit/fleet-<date>.json`, computes the escalation set (container CRITICAL > 0 or reboot pending), and ships a summary to Discord `#alerts` (`tasks/ship_discord.yml`, webhook from Vault `prod/discord/webhook-alerts`).

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/security-audit.yml          # full
ansible-playbook -i inventories/prod/hosts.yml playbooks/security-audit.yml -l harbor # one host/group
ansible-playbook ... -e security_audit_scan_containers=false                          # fast OS-only pass
```

Schedule weekly (CronCreate on the controller, or a systemd timer): `security-audit.yml` Monday 06:00.

## Knobs (`defaults/main.yml`)

`security_audit_scan_containers`, `security_audit_trivy_severity` (HIGH,CRITICAL), `security_audit_severity_gate`, `security_audit_discord_webhook_vault_path`, `security_audit_loki_url`, `security_audit_gitlab_issues` (off until reviewed); for the container scan: `security_audit_trivy_db_room_mb`, `security_audit_trivy_min_free_mb`, `security_audit_trivy_scan_timeout_s`.

## Backup & restore

Class **D** (code) — reports are disposable, regenerated each run. No state to back up.

## Runbook

- No findings shipped? Check `debsecan` installed and the Trivy DB pulled (needs host egress to ghcr/github). `docker run ... aquasec/trivy image --download-db-only` warms the cache.
- Discord silent → `vault kv get prod/discord/webhook-alerts` present; the `#alerts` channel exists (roles/discord_guild).
- Trivy slow first run = database download (about 1.4 GB with the Java index, cached in the `trivy-db` volume afterwards).
- Each image record counts `critical` / `high` (every known entry) and `critical_fixable` / `high_fixable` (a fixed version is published): only the second pair goes away with an upgrade of the image; the rest waits for the distribution or the vendor.
- **"not scanned"** in a host record (`containers[].scanned: false`, `reason`) is never "no findings". Trivy exports an image into a temporary file as large as the image; an image is scanned only when `image + security_audit_trivy_db_room_mb + security_audit_trivy_min_free_mb` fits in the free space of Docker's directory, and a scan is stopped after `security_audit_trivy_scan_timeout_s`. Fix the host (remove superseded images, or grow its disk), then run the audit on that host again.
