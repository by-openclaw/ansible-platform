<!-- Header: ADR compliance audit record — verdaccio, 2026-10-02. Instrument:
     docs/audits/adr-compliance-checklist.md (every row). Evidence gathered live on
     lxc-verdaccio-01, Authentik (ak shell), Prometheus/Loki, npm (plugin registry) and the PVE node;
     the fixes ship in the same PR, applied twice (changed=0). -->

# ADR compliance audit — verdaccio (2026-10-02)

Method: roles/contract_audit (PASS=11 FAIL=0 SKIP=22) + manual walk on the live guest, Authentik, Prometheus/Loki, the npm registry (plugin availability) and the PVE node.

**Service:** `verdaccio` (`roles/verdaccio`, `playbooks/verdaccio.yml`) on `lxc-verdaccio-01` (ct 505) — `npm.<domain>`, private (route internal-only), OIDC via the `verdaccio-openid` plugin, one container built from the official image with the S3 and OpenID plugins, running as uid 10001, packages on SeaweedFS S3, npmjs uplink.
**Verdicts:** **PASS** · **GAP** · **N/A** · **NOT VERIFIED**; gaps are **FIX** (this PR) · **PLATFORM** · **PROPOSE** · **OWNER**. Host-level rows identical to the previous audits carry the same verdict.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | SEC-21, GIT-05 | Base image `6.9.3` while `6.10.4` (2026-09-20) is current; plugins `verdaccio-openid 0.18.0` → `0.19.0`, `verdaccio-aws-s3-storage 12.1.1` → `12.1.2`. | **FIX** — pins (the platform image is rebuilt, the container recreated once) |
| 2 | SVC-16 | The scaffold minted a service mailbox (`mailbox: true`) although Verdaccio sends no mail — a mailbox without a role. | **FIX** — `mailbox: false` (the existing mailbox stays, never deleted — same as Jitsi) |
| 3 | IDN-17, SVC-37 | No `docs/services/verdaccio.md`. | **FIX** — this PR |
| 4 | INF-33 | No application metrics: Verdaccio 6 has no Prometheus endpoint and no plugin for it exists on npm (`verdaccio-prometheus`/`verdaccio-metrics`: not published); `/-/metrics` answers 401 (generic auth). | **note** — not fixable in-product; blackbox + `/-/ping` cover INF-39 |
| 5 | SEC-22 / NAM-01 / INF-35 | Writable rootfs; NetBox empty; no alert rule names verdaccio. | **PLATFORM** |

## Rows

| Area | ID | Verdict | Evidence |
|---|---|---|---|
| naming | NAM-03–08, NAM-17 | PASS | `lxc-verdaccio-01` → internal A/AAAA + PTR; `npm.<domain>` resolves to Traefik inside; CI account `svc-verdaccio-prod` |
| identity | IDN-01/02 | PASS | `verdaccio-openid` against Authentik app `verdaccio` (bound to `verdaccio-users`, 2 members); plugin `authorized-groups`; blueprint `oidc-verdaccio` successful |
| identity | IDN-16/17 | PASS / GAP → fixed | the CI account's credential in Vault (htpasswd seeded once); service page gap 3 |
| secrets | SEC-01–05, SEC-17 | PASS | `secret/{env}/verdaccio/{registry, oidc, s3}` — `vault_secret`, `no_log`; S3 and OIDC secrets injected as environment, `config.yaml` references variables | <!-- pragma: allowlist secret — names of Vault PATHS, no value -->
| database | SVC-26–29 | N/A | the package db lives in the bucket |
| ingress | SVC-01–04, SEC-28 | PASS | Traefik route internal-only; DOCKER-USER admits Traefik on 4873; TLS at Traefik only |
| storage | SVC-52–54 | PASS | bucket `verdaccio` on SeaweedFS (path-style), scoped identity from `seaweedfs_bucket` |
| certs | SEC-26 | PASS | — |
| mailbox | SVC-16 | GAP → fixed | gap 2 |
| decommission | SVC-47 | PASS | catalog row; scaffold concerns with absent paths |
| hardening | SEC-15 | **PASS** | the container runs as uid 10001 (the official image's user) |
| hardening | SEC-20 | PASS | Lynis hardening index **86** |
| hardening | SEC-21 | **GAP** → fixed | gap 1 |
| hardening | SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban active; ufw active (8 rules) |
| logging | INF-27–31 | PASS | journald → promtail → Loki (`container="verdaccio"`, 363 lines/h at level `http`); audit middleware on; 0 errors in 24 h |
| monitoring | INF-33 | note | gap 4 |
| monitoring | INF-34, probe | PASS | `node`, `cadvisor`, blackbox `https://npm.<domain>/` up; `/-/ping` 200 |
| monitoring | INF-35/39 | GAP (platform) | gap 5 |
| backup | INF-41–43 | PASS | PBS ct 505: 20 snapshots, latest 2026-10-02T01:50Z (5.7 GB); packages in the replicated bucket |
| pins | GIT-01–05 | GAP → fixed | gap 1 |
| contract | SVC-23 | PASS | `check_service_contract.py` 32/32; `contract_audit` PASS=11 FAIL=0 |
