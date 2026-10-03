<!-- Header: ADR compliance audit record — monitoring, 2026-10-02. Instrument:
     docs/audits/adr-compliance-checklist.md (every row). Evidence gathered live on
     lxc-monitoring-01 (Prometheus, Alertmanager, Loki and Grafana APIs), the PVE node and the
     upstream release pages; the fixes ship in the same PR, applied twice (changed=0). -->

# ADR compliance audit — monitoring (2026-10-02)

Method: roles/contract_audit (PASS=11 FAIL=0 SKIP=22) + manual walk on the live guest, the four components' APIs, the PVE node and the upstream release pages.

**Service:** `monitoring` (`roles/prometheus`, `blackbox_exporter`, `alertmanager`, `loki`, `grafana`; `playbooks/monitoring.yml`) on `lxc-monitoring-01` (ct 580) — Grafana at `grafana.<domain>` (private, OIDC), Prometheus (117 targets, 14 platform alerts, 15-day TSDB), Alertmanager (mail + Discord), Loki (S3, 90 d), Blackbox (HTTPS/DNS/TCP/TLS/SMTP/ICMP probes); every component a container running as its own system account.
**Verdicts:** **PASS** · **GAP** · **N/A** · **NOT VERIFIED**; gaps are **FIX** (this PR) · **PLATFORM** · **PROPOSE** · **OWNER**. Host-level rows identical to the previous audits carry the same verdict.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | SEC-21, GIT-05 | Pins behind: Prometheus `v2.53.3` (the 2.53 LTS line ended; `v3.13.4` is the current LTS with a 2026 security fix), Alertmanager `v0.28.1` → `v0.34.1`, Blackbox `v0.26.0` → `v0.28.0`, **Grafana `13.2.2` → `13.2.3` (three CVEs, 2026-09-29)**; Loki `3.7.8` current. | **FIX** — pins (each container recreated once; the 2.x TSDB is read as is) |
| 2 | INF-27 | Prometheus, Alertmanager, Loki and Grafana log to `json-file` (the explicit journald driver was missing from their definitions; Blackbox already had it). | **FIX** — `log_driver: journald` on the five definitions |
| 3 | INF-33 | The stack's own components are not scraped (only Prometheus scrapes itself): Alertmanager, Loki, Grafana and Blackbox serve `/metrics` on their loopback listeners. | **FIX** — job `monitoring` (`prometheus_self_targets`) |
| 4 | IDN-17, SVC-37 | No `docs/services/monitoring.md`. | **FIX** — this PR |
| 5 | INF-35, INF-38/39 | 14 platform alerts cover hosts, probes, TLS, PostgreSQL and containers; **no per-service alert or dashboard** (Grafana carries the sample provisioning only) — the deploy gate of every service in this walk. | **PLATFORM** — an alert/dashboard catalog driven by `metrics_port` (candidates listed in each service record) |
| 6 | SEC-22 / NAM-01 | Writable rootfs; NetBox empty. | **PLATFORM** |

## Rows

| Area | ID | Verdict | Evidence |
|---|---|---|---|
| naming | NAM-03–08 | PASS | `lxc-monitoring-01` → internal A/AAAA + PTR; `grafana.<domain>` resolves to Traefik inside; no public record |
| identity | IDN-01/02 | PASS | Grafana generic OAuth against Authentik (`allow_sign_up` for auto-provisioning, `role_attribute_path` maps `grafana-admins` → Admin); the other components have no UI |
| identity | IDN-16/17 | PASS / GAP → fixed | Grafana `admin` password in Vault; service page gap 4 |
| secrets | SEC-01–05, SEC-17 | PASS | `grafana/{admin, db-pgsql, oidc}`, `mail/monitoring`, `discord/webhook-alerts`, `loki/s3` — `vault_secret`, `no_log`; configs 0640 to the service accounts | <!-- pragma: allowlist secret — names of Vault PATHS, no value -->
| database | SVC-26–29 | PASS | Grafana on `grafana` / `grafana` in the cluster, `sslmode=verify-full` (contract_audit) |
| ingress | SVC-01–04, SEC-28 | PASS | Grafana behind Traefik (internal-only); Prometheus, Alertmanager and Blackbox on loopback; Loki `:3100` admitted from the platform ranges only (promtail push); TLS at Traefik |
| storage | SVC-52–54 | PASS | Loki chunks + index in `loki-data` on SeaweedFS (scoped identity); retention 90 d, compactor on |
| certs | SEC-26 | PASS | — |
| mailbox | SVC-16 | PASS | `monitoring@<domain>` (TX: alerts → `alerts@`) + Discord webhook, both from Vault |
| decommission | SVC-47 | PASS | catalog row; scaffold concerns with absent paths |
| hardening | SEC-15 | **PASS** | every component runs as its own account (`prometheus` 102:105, `loki` 104, `grafana` 105, blackbox 102:105) |
| hardening | SEC-20 | PASS | Lynis hardening index **86** |
| hardening | SEC-21 | **GAP** → fixed | gap 1 |
| hardening | SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban active; ufw active (22 rules: Loki push + Grafana from the platform ranges, scrapes, the firewall's syslog relay on 1514) |
| logging | INF-27 | **GAP** → fixed | gap 2 |
| logging | INF-29/32 | PASS | Loki `retention_period: 2160h` (90 d) for every stream — the audit class included; `audit`-labelled streams from every host |
| monitoring | INF-33 | **GAP** → fixed | gap 3 |
| monitoring | INF-34 | PASS | `node`, `cadvisor` up; 117/117 targets up at audit time |
| monitoring | INF-35/36 | PASS / GAP (platform) | 14 alerts, every one with a severity label and a runbook annotation; per-service alerts gap 5 |
| monitoring | INF-38/39 | GAP (platform) | gap 5 (dashboards as code: the sample provisioning only) |
| backup | INF-41–43 | PASS | PBS ct 580: 21 snapshots, latest 2026-10-02T03:01Z (20.7 GB); Grafana DB in the cluster dump; Loki in the replicated bucket; the TSDB (6.8 GB, 15 d) is recreated by scraping |
| pins | GIT-01–05 | GAP → fixed | gap 1 |
| contract | SVC-23 | PASS | `check_service_contract.py` 32/32; `contract_audit` PASS=11 FAIL=0 |

## Closure — 2026-10-03

| Outcome | Gaps |
|---|---|
| **Fixed, applied ×2 (`changed=0`), verified** | 1 (Prometheus `v3.13.4`, Alertmanager `v0.34.1`, Loki `0.28.0`, Grafana `13.2.3` — the five containers recreated once; every scrape target back up after the ~1 min gap), 2 (Prometheus, Alertmanager, Loki and Grafana on journald), 3 (job `monitoring` 4/4 up — Alertmanager, Loki, Grafana, Blackbox scraped on their loopback listeners), 4 (service page) |
| **Platform passes** | 5 (per-service alert rules and dashboards — the monitoring pass after the walk; today's 14 platform rules unchanged), 6 (read-only rootfs, NetBox) |

Idempotence: `monitoring.yml` from the branch — `changed=5` (containers) then `changed=0`; `main` = `changed=0` after the merge. The branch carried the catalog rows merged during the walk (gitlab, gitlab-runner, netbird, netbox, harbor, jitsi, nextcloud): their jobs are up in the same Prometheus.
