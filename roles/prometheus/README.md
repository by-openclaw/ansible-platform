# role: prometheus

Prometheus (a container: `prom/prometheus:<prometheus_version>`, host network, loopback) on `lxc-monitoring-01` (`:9090`; TSDB `/var/lib/prometheus/metrics2`, run as the prometheus account this role owns — alertmanager and blackbox run as it too), node_exporter fleet-wide (`:9100`). Metrics only — NetBox and others deep-link here; **metrics never live in NetBox**.

- Retention window is the only state; scrape targets = inventory.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/monitoring.yml`

## Backup & restore

Class **E** — TSDB scratch; rebuilds. No backup. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `/-/healthy`; targets page all `UP`.
- Common: target down → promtail/node_exporter service on that host.
