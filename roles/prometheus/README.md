# role: prometheus

Prometheus (apt) on `lxc-monitoring-01` (`:9090`), node_exporter fleet-wide (`:9100`). Metrics only — NetBox and others deep-link here; **metrics never live in NetBox**.

- Retention window is the only state; scrape targets = inventory.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/monitoring.yml`

## Backup & restore

Class **E** — TSDB scratch; rebuilds. No backup. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `/-/healthy`; targets page all `UP`.
- Common: target down → promtail/node_exporter service on that host.
