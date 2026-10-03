<!-- Header: ADR compliance audit record — jumpserver, 2026-10-02. Instrument:
     docs/audits/adr-compliance-checklist.md (every row). Evidence gathered live on
     lxc-jumpserver-01 (container definitions), Vault (key names), Prometheus/Loki and the PVE
     node; the fixes ship in the same PR, applied twice (changed=0). -->

# ADR compliance audit — jumpserver (2026-10-02)

Method: roles/contract_audit (PASS=10 FAIL=0 SKIP=23) + manual walk on the live guest, Vault (key names), Prometheus/Loki and the PVE node.

**Service:** `jumpserver` (`roles/jumpserver`, `playbooks/jumpserver.yml`) on `lxc-jumpserver-01` (ct 571) — `jumpserver.<domain>`, private (route internal-only), OIDC via Authentik, JumpServer CE `v4.10.19` (core, celery, koko, lion, web + bundled PostgreSQL 16 and Redis 7), replays on SeaweedFS S3, assets = every managed host reconciled from the catalog.
**Verdicts:** **PASS** · **GAP** · **N/A** · **NOT VERIFIED**; gaps are **FIX** (this PR) · **PLATFORM** · **PROPOSE** · **OWNER**. Host-level rows identical to the previous audits carry the same verdict.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | SEC-17, SEC-13 | **The bundled Redis password rides on its container's command line** (`redis-server --requirepass …`, the vendor's documented form); the audit's container dump printed it into the session log. Rotated in Vault at once. | **FIX** — rotated (the apply recreates Redis and the four consumers with the new value); the role now passes it as `REDIS_PASSWORD` + `--requirepass "$REDIS_PASSWORD"` through the shell so the value is not an argument |
| 2 | SVC-11, SVC-16 | Two Vault documents for one mailbox: the reconcile read a hand-made `jumpserver/smtp` while the mailbox role had minted `mail/jumpserver`. | **FIX** — SMTP from `mail/jumpserver` (one document); the old document is no longer read |
| 3 | IDN-17, SVC-37 | No `docs/services/jumpserver.md`. | **FIX** — this PR |
| 4 | SEC-15 | core, celery, koko, web, lion and the bundled PostgreSQL/Redis run as root (vendor images). | **PROPOSE** — register OH-15 (#724) |
| 5 | SEC-21 | `v4.10.19-ce` = the current v4 line (2026-08-20); upstream shipped **v5.0.0** (2026-09-17) — a major with a new architecture. | **OWNER** — evaluate the v5 move (ladder + migration notes) |
| 6 | INF-33 | JumpServer CE's `/api/v1/prometheus/metrics/` needs an API key; not scraped. | **note** — blackbox covers INF-39; an API-key scrape is a platform item |
| 7 | SEC-22 / NAM-01 / INF-35 | Writable rootfs; NetBox empty; no alert rule names jumpserver. | **PLATFORM** |

## Rows

| Area | ID | Verdict | Evidence |
|---|---|---|---|
| naming | NAM-03–08 | PASS | `lxc-jumpserver-01` → internal A/AAAA + PTR; `jumpserver.<domain>` resolves to Traefik inside |
| identity | IDN-01/02 | PASS | OIDC against Authentik app `jumpserver` (`jumpserver_oidc_enabled: true`); `bastion-admins` + its permission reconciled; local `admin` break-glass in Vault |
| identity | IDN-17 | GAP → fixed | gap 3 |
| secrets | SEC-01–05, SEC-17 | **GAP** → fixed | gap 1; `jumpserver/{app, oidc, s3}`, `mail/jumpserver`, `break-glass/*` read only inside the reconcile and shredded — `vault_secret`, `no_log` | <!-- pragma: allowlist secret — names of Vault PATHS, no value -->
| database | SVC-26–29 | N/A (catalog `db: own`) | bundled PostgreSQL 16 + Redis 7 on the service network, not published |
| storage | SVC-52–54 | PASS | replays in `jumpserver-replays` on SeaweedFS (scoped identity) |
| ingress | SVC-01–04, SEC-28 | PASS | web `:8090` behind Traefik (internal-only); koko/lion reached through the web front; TLS at Traefik |
| certs | SEC-26 | PASS | — |
| mailbox | SVC-16 | GAP → fixed | gap 2 |
| decommission | SVC-47 | PASS | catalog row; scaffold concerns with absent paths |
| hardening | SEC-15 | **GAP** | gap 4 |
| hardening | SEC-20 | PASS | Lynis hardening index **86** |
| hardening | SEC-21 | PASS / OWNER | gap 5 |
| hardening | SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban active; ufw active (8 rules) |
| logging | INF-27–31 | PASS | seven containers journald → promtail → Loki |
| monitoring | INF-33 | note | gap 6 |
| monitoring | INF-34, probe | PASS | `node`, `cadvisor`, blackbox `https://jumpserver.<domain>/` up; core/web/lion healthy |
| monitoring | INF-35/39 | GAP (platform) | gap 7 |
| backup | INF-41 | PASS | PBS ct 571: 21 snapshots, latest 2026-10-02T02:54Z (10.2 GB); replays replicated off-site with the bucket |
| pins | GIT-01–05 | PASS | every image pinned (`v4.10.19-ce`, `postgres:16`, `redis:7-alpine`) |
| contract | SVC-23 | PASS | `check_service_contract.py` 32/32; `contract_audit` PASS=10 FAIL=0 |

## Closure — 2026-10-03

| Outcome | Gaps |
|---|---|
| **Fixed, applied ×2 (`changed=0`), verified** | 1 (the Redis password rotated in Vault and handed to `redis-server` through `$REDIS_PASSWORD` — the container's command line carries no literal; `redis-cli … ping` with the environment value → `PONG`; the seven containers recreated once, core/lion/web/postgres/redis healthy), 2 (SMTP from the one mailbox document: the reconcile reports `email: SMTP -> mail.<domain>:587 as jumpserver@<domain>`), 3 (service page) |
| **Decision pending (owner)** | 4 (register OH-15 in #724), 5 (v5.0.0 — a major: evaluate) |
| **Platform passes / notes** | 6 (metrics behind an API key — monitoring pass), 7 (read-only rootfs, NetBox, per-service alert rules) |

Idempotence: `jumpserver.yml` from the branch — `changed=3` (containers) then `changed=0`; `main` = `changed=0` after the merge. Found on the way: a `# pragma` comment inside a folded block scalar is part of the Jinja expression (the first apply stopped at the email config; fixed with `dict`/`zip`).
