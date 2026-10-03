# Monitoring stack — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: monitoring`, role `grafana` as the pin owner). Roles `roles/prometheus`, `roles/blackbox_exporter`, `roles/alertmanager`, `roles/loki`, `roles/grafana` (+ `roles/promtail` on every host), play `playbooks/monitoring.yml`, guest `lxc-monitoring-01` (ct 580). Audit: [`docs/audits/monitoring-2026-10-02.md`](../audits/monitoring-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — Grafana's generic OAuth against Authentik (role mapping: `grafana-admins` → Admin, everyone else Viewer, auto-provisioned); Prometheus, Alertmanager, Loki and Blackbox have no user interface of their own (loopback listeners; Grafana is the front).
2. **Authentik application:** OIDC, slug `grafana` (`group_vars/all/sso.yml`).
3. **Access model:** sign-in through Authentik only (`grafana.<domain>`, route internal-only); admins by group claim; no local sign-up. Break-glass: Grafana's local `admin` with its password in Vault.
4. **Vault paths:** `secret/{env}/grafana/admin`, `grafana/db-pgsql` (`postgres_db`), `grafana/oidc` (`roles/authentik`), `mail/monitoring` (Alertmanager's mailbox), `discord/webhook-alerts`, `loki/s3` (`seaweedfs_bucket`).
5. **Ansible adapter + vars:** the five roles' `defaults/main.yml` (pins, listeners, retention, self-targets) and templates (`prometheus.yml.j2` + `platform.rules.yml.j2`, `alertmanager.yml.j2`, `loki.yaml.j2`, `grafana.ini.j2` + provisioning, `blackbox.yml.j2`); `service_scaffold` runs each container as its own system account.
6. **Removal notes:** `playbooks/decommission-service.yml`; class B/C — Grafana's database (cluster PostgreSQL) and the Loki bucket `loki-data` are archived before destroy; the Prometheus TSDB (15 d) is not kept.

## Notifications (services/0005)

1. **Transport:** Alertmanager → mail through the `monitoring@<domain>` mailbox (STARTTLS 587) to the central `alerts@` sink, and the Discord `#alerts` webhook; grouped by alert name.
2. **What is sent:** the platform alerts (`platform.yml`: 15 rules, each with a severity and a runbook) — resolver, probes, TLS expiry, targets down, disk, memory, SeaweedFS slots, Alertmanager reachability, PostgreSQL, container restarts and memory.
3. **Alerting path:** Prometheus (self + `node`, `cadvisor`, blackbox jobs + every service's `/metrics`) → Alertmanager → mail + Discord; the stack's own components are scraped as job `monitoring`.
4. **Logs:** every host's promtail → Loki (`loki-data` on SeaweedFS, 90-day retention; `audit`-labelled streams per host); the stack's containers → journald → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B/C (`docs/backup.md`): Grafana's database in the shared PostgreSQL cluster (daily `pg_dumpall`), Loki chunks and index in the S3 bucket `loki-data` (replicated off-site), the guest image in PBS (daily, ct 580). The Prometheus TSDB (15 d, local) is recreated by scraping; dashboards and rules are code.

## What Prometheus keeps — the pacemaker rule (owner direction 2026-10-03)

Monitoring answers one question first: **is the platform alive, and if not, where?** Prometheus therefore keeps the series the rules read and a small set of capacity signals — not everything an exporter can emit.

- `prometheus_keep` (`roles/prometheus/defaults/main.yml`) names, per job, the metric families that are kept; everything else is dropped at scrape time. Jobs with a keep-list today: `node`, `cadvisor`, `gitlab`, `monitoring`. `prometheus_drop` removes label combinations after the keep (systemd unit states other than `failed`).
- Measured on 2026-10-03: the exporters offer ≈185,000 samples per scrape, Prometheus keeps ≈25,500.
- **A new rule or dashboard that needs another family adds it to `prometheus_keep` in the same change.** No per-service dashboard or alert set is added by default: a signal is added when it has an action (`infra/0007`: no alert without an action).
- The liveness set (15 rules): target down, URL probe failed, resolver down, certificate expiring (two levels), host disk almost full, host out of memory, **storage pool not ONLINE**, PostgreSQL down / connections (two levels), container restarting, container memory near its limit, object-store volume slots low, Alertmanager unreachable.
