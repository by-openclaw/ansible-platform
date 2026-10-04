<!-- Header: ADR compliance audit record — postgresql (the shared cluster), 2026-10-03. Instrument:
     docs/audits/adr-compliance-checklist.md (every row). Evidence gathered live on lxc-pgsql-01
     (psql as the local superuser: settings, hba, roles, databases, connections; container; backup unit —
     read-only, addresses redacted), Prometheus/Loki; the fixes ship in the same PR, applied twice (changed=0). -->

# ADR compliance audit — postgresql (2026-10-03)

Method: roles/contract_audit (PASS=10 FAIL=0 SKIP=23) + manual walk on the live guest, Prometheus/Loki.

**Service:** `postgresql` (`roles/postgresql`, `playbooks/postgresql.yml`) on `lxc-pgsql-01` — PostgreSQL `17.11` (official image, `pgdata` volume 438 MB), 12 databases for 11 services, TLS 1.2+ with the platform wildcard, `scram-sha-256`, `hostssl` from the service networks, daily `pg_dumpall`, `postgres_exporter` sidecar.
**Verdicts:** **PASS** · **GAP** · **N/A** · **NOT VERIFIED**; gaps are **FIX** (this PR) · **PLATFORM** · **PROPOSE** · **OWNER**. Host-level rows identical to the previous audits carry the same verdict.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | SEC-23, INF-29 | **No DDL audit**: `log_statement = none` and `log_disconnections = off` — the server log says who connected and nothing about schema changes or session ends. | **FIX** — `log_statement = ddl`, `log_disconnections = on` (server flags; one container recreate ≈ 10 s of connection resets, announced) |
| 2 | SEC-28 (TLS) | `ssl_ciphers = HIGH:MEDIUM:+3DES:!aNULL` (the default) still offers MEDIUM and 3DES suites behind the TLS 1.2 floor. | **FIX** — `HIGH:!aNULL:!MD5:!3DES:!RC4` (same recreate) |
| 3 | IDN-17, SVC-37 | No `docs/services/postgresql.md`. | **FIX** — this PR |
| 4 | SEC-15 | The server container runs as root (the official image's entrypoint drops to `postgres`, uid 999). | **PROPOSE** — register OH-19 (#724): entrypoint-drop class, like the bundled databases |
| 5 | INF-43 (at rest) | `data_checksums = off` (an initdb-time choice: enabling needs `pg_checksums` on a stopped cluster). | **OWNER** — a maintenance window (≈ minutes for 438 MB) |
| 6 | tuning | `shared_buffers = 128MB` (image default) for 12 databases / 200 connections. | **PLATFORM** — the per-service tuning pass |
| 7 | SEC-22 / NAM-01 / INF-35 | Writable rootfs; NetBox empty; the platform's PostgreSQL alerts exist (connections, replication) — no per-database rule. | **PLATFORM** |

## Rows

| Area | ID | Verdict | Evidence |
|---|---|---|---|
| naming | NAM-03–08 | PASS | `lxc-pgsql-01` → internal A/AAAA + PTR; no service FQDN (clients use the host name, `verify-full` against the wildcard) |
| identity | IDN-01 | N/A / PASS | no UI; one role per service (`authentik, gitlab, grafana, grc, harbor, netbird, netbox, nextcloud, pgadmin, vaultwarden, …` — none superuser, none createrole), `pgadmin_dba` (predefined roles), `postgres_exporter`; the superuser `postgres` break-glass in Vault |
| identity | IDN-17 | GAP → fixed | gap 3 |
| secrets | SEC-01–05 | PASS | every password minted into Vault by `roles/postgres_db` and ALTERed to match on each run; `POSTGRES_PASSWORD` from Vault at container start; `password_encryption = scram-sha-256` | <!-- pragma: allowlist secret — names of settings and paths, no value -->
| database | SVC-26–31 | PASS | 12 databases, PUBLIC `CONNECT` revoked on every service database (0 of 11 grant it); every live client session on TLS (`pg_stat_ssl`: authentik 30, gitlab 28, vaultwarden 6, grc 5, grafana 4, netbird 3, harbor 2, pgadmin 1, exporter 1 — all `ssl=true`; the only non-TLS session is the local superuser socket) |
| ingress | SVC-01–04, SEC-28 | PASS / GAP → fixed | published on the service address (v4 + v6) and loopback only; `pg_hba`: `hostssl … scram-sha-256` from the service CIDRs, loopback scram, local trust (container socket), exporter from the Docker gateway; ufw 9 rules; gap 2 |
| certs | SEC-26/27 | PASS | the Let's Encrypt wildcard on the server (`ssl_cert_file`, valid to 2026-11-21), `ssl_min_protocol_version = TLSv1.2`; clients `verify-full` |
| mailbox | SVC-16 | N/A | sends no mail |
| hardening | SEC-15 | GAP (proposal) | gap 4 |
| hardening | SEC-20 | PASS | Lynis hardening index **86** |
| hardening | SEC-21 | PASS | `postgres:17.11` = the newest 17.x tag (Docker Hub, 2026-10-03) |
| hardening | SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban |
| logging | INF-27–31 | PASS / GAP → fixed | server log → journald → Loki (`log_connections on`, `log_checkpoints on`); gap 1 |
| monitoring | INF-33/34 | PASS | `postgres_exporter` v0.19.0 (`:9187`, runs as `nobody`) scraped; `node`, `cadvisor` |
| monitoring | INF-35/39 | PASS / GAP (platform) | platform PostgreSQL alerts; gap 7 |
| backup | INF-41–43 | PASS / OWNER | `pg-backup.timer` 02:00 (last run 2026-10-03 02:00 rc=0; 4 daily dumps ≈ 42 MB each, 7 d retention) in the PBS image (encrypted, S3 replica); gap 5 |
| pins | GIT-01–05 | PASS | `postgres:17.11`, exporter `v0.19.0` |
| contract | SVC-23 | PASS | `check_service_contract.py` 32/32 |

## Closure — 2026-10-03

| Outcome | Gaps |
|---|---|
| **Fixed, applied ×2 (`changed=0`), verified** | 1 (`log_statement = ddl`, `log_disconnections = on` live: a probe `CREATE/DROP TABLE` shows in the server log, session ends are logged), 2 (`ssl_ciphers = HIGH:!aNULL:!MD5:!3DES:!RC4`; every client session back on TLS after the one restart — authentik, gitlab, grafana, grc, harbor, netbird, vaultwarden, the exporter), 3 (service page) |
| **Decision pending (owner)** | 4 (register OH-19 in #724), 5 (`data_checksums` — a maintenance window) |
| **Platform passes** | 6 (tuning: `shared_buffers`), 7 (read-only rootfs, NetBox, per-database alert rules) |

Idempotence: `postgresql.yml` from the branch — `changed=1` (the container with the three flags; one restart at 11:23Z, ≈10 s) then `changed=0`; exporter `pg_up 1`; no HTTP probe failing afterwards; `main` = `changed=0` after the merge.

## Owner decisions applied after the closure

- **2026-10-03 window — gap 5:** `data_checksums = on`. `pg_data_checksums: true` in the role; `tasks/checksums.yml` converted the cluster once (fresh `pg_dumpall` first; clean stop, control file "shut down", `pg_checksums --enable`: 20,241 files, 70,395 blocks; database back after ≈4 min); new clusters are initialised with `--data-checksums`; every run asserts the live setting. `postgresql.yml` `changed=3` then `changed=0`; 126/126 targets and 44/44 probes up afterwards.

## High availability and hardening — 2026-10-04 (#781)

- **Cluster (services/0004):** the server is one of three members under Patroni (`lxc-pgsql-01` leader, `-02` synchronous standby, `-03` replica; etcd colocated). The data directory of this audit was adopted unchanged: same system identifier before and after, 12 databases, 15 logins, checksums on; the port was closed for 3 s at 07:03Z, a fresh dump was taken first. Consumers connect through the data endpoint (`docs/audits/dbproxy-2026-10-04.md`).
- **Gap 4 (SEC-15) closed:** the container starts as `postgres` (the platform image sets the user); OH-19 is closed in `docs/override-hardening.md`.
- **Gap 7 (SEC-22) closed for this service:** read-only root filesystem, every capability dropped, on the three members, their exporters and etcd.
- **New rules:** `PostgresLeaderCount`, `PostgresReplicaMissing`, `PostgresEndpointNoLeader`.
- Still open: gap 6 (tuning), NetBox (platform), the ADR departures proposed in doc-platform-core #72.
