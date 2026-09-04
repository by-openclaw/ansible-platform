# role: grafana

Grafana (apt) on `lxc-monitoring-01` (`:3000`, `grafana.<domain>`), Authentik OAuth (`grafana-admins`), `grafana` DB in cluster Postgres (`ssl_mode=verify-full`), datasources Prometheus + Loki. Alerting/Alertmanager = parked.

- Dashboards/provisioning = code in the role; DB holds users/prefs.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/monitoring.yml`

## Backup & restore

Class **A + D**: PG dump covers the DB; provisioning re-renders from code. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `/api/health` → `database: ok`; `systemctl is-active grafana-server`.
- Common: DB auth failure after rotation → rerun `monitoring.yml`.
