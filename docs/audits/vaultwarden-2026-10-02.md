<!--
  ADR compliance audit — Vaultwarden. Instrument: docs/audits/adr-compliance-checklist.md.
  Method: roles/contract_audit (PASS=12 FAIL=0 SKIP=21) + manual walk on the live guest.
-->
# ADR compliance audit — Vaultwarden (2026-10-02)

**Service:** `vaultwarden` (`roles/vaultwarden`, `playbooks/vaultwarden.yml`) on `lxc-vaultwarden-01` (ct 502) — `vaultwarden.<domain>`, public, native OIDC, shared PostgreSQL, class A, image `vaultwarden/server:1.37.1` (web-vault 2026.6.0).
**Verdicts:** **PASS** · **GAP** · **N/A** · **NOT VERIFIED**; gaps are **FIX** (this PR) · **PLATFORM** · **PROPOSE**. Host-level rows identical to the previous audits carry the same verdict.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | SVC-33–36, SEC-01 | **Mail went to an external relay** (`smtp.resend.com`, sender `no_reply@resend.<domain>`, credential `{env}/resend/<org>` — the retired Resend path) although the scaffold already provisions the `vaultwarden@` mailbox at our Mailcow. The role no longer sets any `SMTP_*` at all: the running container carried **stale environment** from a 2026-09-02 deploy that nothing managed. Invitations/2FA/new-device mails: unverified for a month. | **FIX** — this PR: SMTP from the service mailbox (`{env}/mail/vaultwarden`, STARTTLS 587), explicit in `vars/main.yml` |
| 2 | IDN-01 | `SSO_ONLY=false`: an existing account could log in with its master password alone, bypassing Authentik. | **FIX** — this PR: `SSO_ONLY=true`; `SSO_ALLOW_UNKNOWN_EMAIL_VERIFICATION=false` (Authentik asserts `email_verified`) |
| 3 | IDN-16, SVC-01 | The break-glass **`/admin` panel answered on the public route** (token-protected, but reachable from the internet). | **FIX** — this PR: `admin_only` endpoint (new in `roles/traefik_route`): internal + admin sources only, app stays public |
| 4 | INF-32 | No organisation event log (`ORG_EVENTS_ENABLED` unset) — the product's own audit trail was off. | **FIX** — this PR: on, 90-day retention |
| 5 | SEC-21 | Pin `1.37.1`; upstream `1.37.3` (2026-09-13) is pullable (tag checked on Docker Hub). | **FIX** — this PR |
| 6 | SEC-15 | The container runs as **root** (PID 1 uid 0); the vendor documents `--user` only, which the ADR rejects. | **PROPOSE** — doc-platform-core #68; register OH-6 (#724) |
| 7 | IDN-17, SVC-37 | No `docs/services/vaultwarden.md`. | **FIX** — this PR |
| 8 | SVC-23 (platform) | Stale container environment survived every apply: the scaffold compares `env` with Docker's default `allow_more_present`, so variables the role stopped managing stay forever. | **PLATFORM** — scaffold `comparisons: {env: strict}` after a fleet dry-run (own PR) |
| 9 | SEC-22 / SEC-23 / NAM-01 / INF-35 | Writable rootfs; auditd inactive (LXC); NetBox empty; no metrics (the product exposes none). | **PLATFORM** / N/A |

## Rows

| Area | ID | Verdict | Evidence |
|---|---|---|---|
| naming | NAM-03–08 | PASS | `lxc-vaultwarden-01` → `10.1.3.160`; `vaultwarden.<domain>`; PTR = asset FQDN |
| identity | IDN-01/02 | GAP → fixed | native OIDC (`SSO_ENABLED`), `restrict_to_group vaultwarden-admins`, `force_email_verified`, `offline_access`; gap 2 |
| identity | IDN-16 | GAP → fixed | `ADMIN_TOKEN` (argon2) in Vault `{env}/vaultwarden/admin`; panel exposure gap 3; alert on use = platform (Vault audit) |
| identity | IDN-17 | GAP → fixed | gap 7 |
| secrets | SEC-01–05, SEC-17 | PASS / GAP | admin token, OIDC client, `db-pgsql`, mailbox credential in Vault (`vault_secret`, `no_log`); gap 1 used a retired external credential |
| database | SVC-26–29 | PASS | own DB/role on the shared cluster, `sslmode=verify-full` (contract_audit), `db-pgsql` document |
| ingress | SVC-01–04 | PASS / GAP | Traefik public route + rate limit, backend bound to the SVC address, ufw admits Traefik only; gap 3 |
| certs | SEC-08–10 | PASS | wildcard at Traefik; PG verify-full with the system CA bundle |
| mail | SVC-33–37 | **GAP** → fixed | gaps 1, 7 |
| hardening | SEC-15 | **GAP** | gap 6 |
| hardening | SEC-20 | PASS | Lynis hardening index **86** |
| hardening | SEC-21 | GAP → fixed | gap 5 |
| hardening | SEC-22/23 | GAP (platform) | gap 9 |
| hardening | SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban (contract_audit) |
| hardening | SEC-30 (app) | PASS | `SIGNUPS_ALLOWED=false`, invitations only, admin token argon2 |
| logging | INF-27–31 | PASS | journald → Loki (`container="vaultwarden"`; 4 lines in 7 days — a quiet product) |
| logging | INF-32 | GAP → fixed | gap 4 |
| monitoring | INF-33/34 | PASS | `node`, `cadvisor`, blackbox `vaultwarden/` up |
| backup | INF-41 | PASS | class A: PG dump + `vaultwarden-data` in PBS (ct 502: 21 snapshots, latest 2026-10-02T01:37Z) |
| pins | GIT-01–05 | PASS → bumped | gap 5 |
| contract | SVC-23 | PASS / platform gap | `check_service_contract.py` 32/32; `contract_audit` PASS=12 FAIL=0; gap 8 |


## Closure — 2026-10-02

| Outcome | Gaps |
|---|---|
| **Fixed, applied ×2 (`changed=0`), verified** | 1 (SMTP via the service mailbox: admin API test mail → Mailcow `sasl_username=vaultwarden@…`, `status=sent`; no Resend variable left in the container), 2 (`SSO_ONLY=true`, `SSO_ALLOW_UNKNOWN_EMAIL_VERIFICATION=false`), 3 (`/admin` router with the internal+admin ipAllowList, 7 ranges; app router public), 4 (`ORG_EVENTS_ENABLED`, 90 d), 5 (`1.37.3`), 7 (service page) |
| **Decision pending (owner)** | 6 (doc-platform-core #68 + register OH-6 in #724) |
| **Platform passes** | 8 (scaffold `env: strict` after a fleet dry-run — stale environment survived a month here), 9 (read-only rootfs, auditd, NetBox) |

Found on the way, fixed in the concern roles: `roles/traefik_route` per-endpoint `admin_only` (reusable for every break-glass UI); `roles/service_scaffold` pulls pinned images under `--check` so an image bump can be dry-run.
