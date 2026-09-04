# role: loki

Loki (apt) on `lxc-monitoring-01` (`:3100`, gRPC `:9096`). Every host ships via `promtail` (journal + container labels, auditd, vault_audit, traefik_access/error, harbor_components). Retention ≥30d (audit services ≥90d).

- `/var/lib/loki` = WAL/cache/compactor scratch **only**.
- Query labels: `job`, `host`, `unit`, `container`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/monitoring.yml`

## Backup & restore

Class **E** — retention window; no backup. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `GET /ready`; `curl /loki/api/v1/label/job/values` lists the expected jobs.
- Common: a host missing → `systemctl is-active promtail` there; new file logs → `promtail_extra_file_jobs` in that group's vars.
