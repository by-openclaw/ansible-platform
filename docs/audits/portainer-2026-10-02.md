<!-- Header: ADR compliance audit record — portainer, 2026-10-02. Instrument:
     docs/audits/adr-compliance-checklist.md (every row). Evidence gathered live on
     lxc-portainer-01 (console API, container definitions), Prometheus/Loki and the PVE node. -->

# ADR compliance audit — portainer (2026-10-02)

Method: roles/contract_audit (PASS=11 FAIL=0 SKIP=22) + manual walk on the live guest, the console API (`/api/status`, `/api/settings/public`), Prometheus/Loki and the PVE node.

**Service:** `portainer` (`roles/portainer`, `playbooks/portainer.yml`) on `lxc-portainer-01` (ct 511) — `portainer.<domain>`, private (route internal-only), OAuth via Authentik, Portainer CE `2.45.1` (= upstream latest) with one Docker agent on every Docker host and the Kubernetes agent in k3s; break-glass admin password by file from Vault; shared agent key from Vault.
**Verdicts:** **PASS** · **GAP** · **N/A** · **NOT VERIFIED**; gaps are **FIX** (this PR) · **PLATFORM** · **PROPOSE** · **OWNER**. Host-level rows identical to the previous audits carry the same verdict.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | IDN-17, SVC-37 | `docs/services/portainer.md` was a setup runbook without the identity / notifications / backup sections. | **FIX** — the three sections prepended |
| 2 | SEC-15 | The console container runs as root (vendor image); the agents are OH-2 already. | **PROPOSE** — register OH-14 (#724) |
| 3 | INF-33 | No Prometheus endpoint in Portainer CE (`/metrics` 404). | **note** — blackbox covers INF-39 |
| 4 | SEC-22 / NAM-01 / INF-35 | Writable rootfs; NetBox empty; no alert rule names portainer. | **PLATFORM** |

## Rows

| Area | ID | Verdict | Evidence |
|---|---|---|---|
| naming | NAM-03–08 | PASS | `lxc-portainer-01` → internal A/AAAA + PTR; `portainer.<domain>` resolves to Traefik inside |
| identity | IDN-01/02 | PASS | `AuthenticationMethod: OAuth` (3) with Authentik's authorize URL; configured by `tasks/sso.yml`; local `admin` break-glass (`RequiredPasswordLength: 12`, password file from Vault) |
| identity | IDN-16/17 | PASS / GAP → fixed | gap 1 |
| secrets | SEC-01–05, SEC-17 | PASS | `secret/{env}/portainer/{admin, agent, oidc}` — `vault_secret`, `no_log`; the admin password by `--admin-password-file`, the agent key as `AGENT_SECRET` (runtime env) | <!-- pragma: allowlist secret — names of Vault PATHS, no value -->
| database | SVC-26–29 | N/A | BoltDB in `portainer-data` |
| ingress | SVC-01–04, SEC-28 | PASS | console `:9000` behind Traefik (internal-only); agents `:9001` admitted from the console only (ufw + DOCKER-USER `from: [portainer]` on every host); TLS at Traefik |
| certs | SEC-26 | PASS | the console's own `:9443` is not published; TLS only at Traefik |
| mailbox | SVC-16 | N/A | sends no mail |
| decommission | SVC-47 | PASS | `tasks/absent.yml` (console, agents, k8s agent); catalog row |
| hardening | SEC-15 | **GAP** | gap 2 |
| hardening | SEC-20 | PASS | Lynis hardening index **86** |
| hardening | SEC-21 | PASS | `2.45.1` = upstream latest (2026-09-17), agents on the same pin |
| hardening | SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban active; ufw active (12 rules) |
| logging | INF-27–31 | PASS | console + agents journald → promtail → Loki; 0 errors in 24 h |
| monitoring | INF-33 | note | gap 3 |
| monitoring | INF-34, probe | PASS | `node`, `cadvisor`, blackbox `https://portainer.<domain>/` up; `/api/status` 200 |
| monitoring | INF-35/39 | GAP (platform) | gap 4 |
| backup | INF-41 | PASS | class D; PBS ct 511: 12 snapshots, latest 2026-10-02T02:08Z (5.3 GB) |
| pins | GIT-01–05 | PASS | `portainer_version` pinned, never `:latest` |
| contract | SVC-23 | PASS | `check_service_contract.py` 32/32; `contract_audit` PASS=11 FAIL=0 |

## Closure — 2026-10-02

| Outcome | Gaps |
|---|---|
| **Verified, no code change** | `portainer.yml -l lxc-portainer-01` from the branch: `ok=176 changed=0` — the live console matches the role (pin, OAuth, admin password from Vault, internal-only route, DOCKER-USER rule); service page committed |
| **Decision pending (owner)** | the console runs as root (vendor image) — register OH-14 in #724 |
| **Platform passes** | read-only rootfs, NetBox, per-service alert rules; the fleet agents play (`portainer.yml` on every Docker host) is applied in the next idle window, not during the walk's parallel applies |

Idempotence: `changed=0` on the console host; `main` = `changed=0` after the merge.
