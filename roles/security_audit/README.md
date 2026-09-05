# role: security_audit

Read-only fleet **CVE / update-currency audit** (identity/0008 · security). It **detects**, never patches — remediation is `roles/updates` (staged waves, `playbooks/updates.yml`).

## What it checks (four layers)

| Layer | Tool | Sees |
|---|---|---|
| **OS** | `debsecan` (Debian CVE↔package) + `apt-get -s dist-upgrade` + `/var/run/reboot-required` | host CVEs with a fix available, security-update count, pending reboot |
| **Containers** | **Trivy** (`aquasec/trivy:0.58.1`, cached DB volume) against every **running** image | the real service CVE surface — host apt cannot see inside containers |
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

`security_audit_scan_containers`, `security_audit_trivy_severity` (HIGH,CRITICAL), `security_audit_severity_gate`, `security_audit_discord_webhook_vault_path`, `security_audit_loki_url`, `security_audit_gitlab_issues` (off until reviewed).

## Backup & restore

Class **D** (code) — reports are disposable, regenerated each run. No state to back up.

## Runbook

- No findings shipped? Check `debsecan` installed and the Trivy DB pulled (needs host egress to ghcr/github). `docker run ... aquasec/trivy image --download-db-only` warms the cache.
- Discord silent → `vault kv get prod/discord/webhook-alerts` present; the `#alerts` channel exists (roles/discord_guild).
- Trivy slow first run = DB download (~40 MB, cached in the `trivy-db` volume afterwards).
