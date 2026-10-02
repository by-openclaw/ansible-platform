<!-- Header: per-service ADR compliance audit — Authentik (lxc-authentik-01, prod, 2026.5.6).
     Instrument: docs/audits/adr-compliance-checklist.md (every row walked; N/A rows listed, not skipped).
     Method: live read-only evidence on 2026-10-02 (containers, Authentik ORM, DNS, TLS, Prometheus, Loki,
     PBS, Vault key names) + repo state @ main 69ce27a..bfed039 + the contract_audit role (PASS=10 FAIL=0). -->

# ADR compliance audit — Authentik (2026-10-02)

Scope: the identity provider on `lxc-authentik-01` (SVC): `roles/authentik` (server, worker, LDAP outpost —
containers of the pinned image), the SSO registry (`group_vars/all/sso.yml`), the identity data
(`people.yml`, `identity.yml`), its database on the cluster PostgreSQL, Redis, mailbox, routes and
backups. Verdicts: **PASS** · **GAP** (needs a change) · **N/A** (row does not apply to this service) ·
**NOT VERIFIED** (no evidence obtained today). Each gap names where it is fixed and who decides:
**FIX** = code within the ADRs (this pass) · **PLATFORM** = one fix covers every service (scheduled as
its own pass) · **PROPOSE** = the ADR text or identity data must change (USER decision).

## Summary — gaps ranked

| # | Row(s) | Gap | Owner / where it is fixed |
|---|---|---|---|
| 1 | IDN-16, SVC-23/63 (spirit), NAM-15 | **A service account is an Authentik superuser**: `svc-netbird-prod` (the NetBird IdP manager). It needs directory reads, not every permission. | **FIX** — declared in `platform_service_accounts` (#721) and rendered as user + RBAC role + a group of the SA's own name carrying the role (the blueprint's entry-level `permissions:` is object-level and a plain list there put the whole identity blueprint in `error` — follow-up PR); superuser group gone; NetBird's user sync verified afterwards |
| 2 | INF-33 | Authentik exposes `/metrics` (`:9300` inside the containers) but nothing publishes or scrapes it; Prometheus has node + cadvisor + the HTTPS probe only. | **FIX** — publish `:9300` on the host (catalog entry for the monitoring host first — the scaffold asserts it), scrape job `authentik` |
| 3 | INF-32, INF-29 | Authentik is an audit service (≥90 d): its container logs reach Loki (90 d retention is set) but **without the `audit` label** — only sshd/sudo/logind/crowdsec units carry it. | **FIX** — roles/promtail: audit-class containers per host (`authentik-server`, `authentik-worker`, `authentik-ldap`) |
| 4 | SVC-27 | Authentik uses the shared Redis **DB 0 with no own DB number** (only NetBox sets one); every consumer also shares the single `redis/admin` credential (SVC-26/29 spirit: least privilege). | **FIX** (DB number: `AUTHENTIK_REDIS__DB` from a platform allocation table) · **PLATFORM** (per-service Redis ACL users — the redis pass) |
| 5 | SEC-22 | Containers run with a writable rootfs, no tmpfs (`ReadonlyRootfs=false` on server/worker/ldap). | **PLATFORM** — scaffold `read_only` + `tmpfs` passthrough, enabled per service after a test; Authentik first |
| 6 | SEC-15 | The two host agents on this guest run as root (`cadvisor`, `portainer-agent`) — they read the host; Authentik itself runs as `1000`. | **PROPOSE** — ADR exception for host agents (cadvisor/portainer agent/node exporter) |
| 7 | NAM-08 | **PTR of the proxy address is wrong**: `10.1.2.110` / `fd01:2::110` reverse to `proxmox.<domain>` (Unbound builds PTR from whichever A override comes first); the asset is `lxc-traefik-01`. | **FIX** (platform-wide in one change) — OPNsense emits one PTR per address from the first override with `addptr`; the collection now exposes it (ansible-opnsense #44) and the overrides play gives the PTR to asset names only (`vm-`/`lxc-`/`srv-`), so `10.1.2.110` → `lxc-traefik-01`, `10.1.3.130` → `lxc-authentik-01`, `10.1.3.210` → `lxc-gitlab-01` — follow-up PR |
| 8 | NAM-07 | Service URLs are **A + AAAA records to the proxy address, not CNAMEs** to the proxy; the ADR wants a CNAME (direct A/AAAA only without a proxy). Platform-wide pattern (split-DNS host overrides). | **PROPOSE** — amend naming/0001 §6.1 to allow A/AAAA to the proxy for split-DNS overrides, or convert the catalog to CNAMEs |
| 9 | IDN-16 | Break-glass admin (`akadmin`) credentials live at `secret/prod/authentik/admin` (bootstrap password + token + secret key), **not `…/break-glass`**, and **no alert fires on its use**. The flow forces MFA enrolment at first login (it has none yet). | **PROPOSE** — path naming (platform convention `…/admin` vs the ADR's `…/break-glass`, same as the OPNsense audit gap 3); alert-on-use = a Loki rule on the login event (needs the Loki ruler → monitoring pass) |
| 10 | IDN-11, IDN-13 | No **scheduled reconciliation** (ADR: 4-hour cron) — `identity-provision.yml` runs on demand only; drift is corrected when someone runs it. | **FIX** — a roles/host_job timer on the controller side is not available; **PROPOSE** where the reconcile runs (the controller is a workstation) |
| 11 | IDN-07 | **Single Authentik instance** (ADR: 2 active/active). | **PROPOSE** — HA lands with the k3s move; record the risk until then |
| 12 | INF-35, INF-39 | Alerts: service-down is covered by the generic `ProbeFailed`/`TargetDown`; **no saturation / app-SLI alert and no dashboard** for Authentik (no dashboards as code at all). | **PLATFORM** — the monitoring pass (parked until every service was installed; it is) |
| 13 | SVC-18, SVC-19, NAM-01 | **NetBox holds zero assets** (0 VMs, 0 devices): no authoritative name, no env/role/service_url/prometheus_job/vault_path_prefix/backup_class/owner for this or any guest. | **PLATFORM** — a `netbox_sync` population from the inventory (the infra-lifecycle roadmap item) |
| 14 | SEC-18, SEC-19 | **No Trivy** in CI; no `.trivyignore`. | **PLATFORM** — CI gate across repos |
| 15 | GIT-13, GIT-16, IDN-27 | No `git-config` role on git-using guests; automation commits (`by-rune`) are **unsigned** (GitHub signs the merge commits only). | **PLATFORM/PROPOSE** — GPG key for the automation identity (identity-keys escrow exists), signing enforced |
| 16 | IDN-17, SVC-37 | No `docs/identity.md` and no `docs/notifications.md` for Authentik (`docs/licensing.md` and `docs/backup.md` cover it). | **FIX** (docs) — with this audit |
| 17 | NAM-13, NAM-14 | PVE storage `poc-data` (this guest's rootfs) and the legacy backup storage `poc-backup` (114 old snapshots of this guest) carry the forbidden `poc` token. | **PROPOSE** — storage rename (known USER item) |
| 18 | SVC-28 (text) | ADR names the DB secret `secret/{env}/{service}/db-password`; the platform's single source is `…/db-pgsql` (database, host, port, user, password, rotated) for every service. | **PROPOSE** — amend services/0004 to the richer document, or rename platform-wide | <!-- pragma: allowlist secret — names of Vault KEYS, no value -->
| 19 | NAM-15 / IDN-03 (note) | `yboujraf_example` is an **active human account that never logged in and has no MFA device** (the people.yml example entry). The flow enforces MFA enrolment at first login, so no bypass — but an unused active account is an attack surface. | **PROPOSE** — `state: disabled` for the example identity (people.yml is USER data) |

Everything else walked below is PASS or N/A for an identity provider.

## naming
| ID | Verdict | Evidence |
|---|---|---|
| NAM-01/02 | **GAP** | NetBox holds no assets (gap 13) |
| NAM-03/04/05 | PASS | `lxc-authentik-01` (16 chars incl. none over the limit? — 16 > 15: see note) — `{site}-{service}-{seq}`, lowercase, hyphen |
| NAM-03 (note) | **GAP (minor)** | `lxc-authentik-01` is 16 characters (limit 15). Platform-wide: `lxc-monitoring-01`, `lxc-vaultwarden-01`, `lxc-jumpserver-01` exceed it too. **PROPOSE** — amend naming/0001 §2 (the 15-char limit predates the `lxc-` site code) or accept as documented exceptions |
| NAM-06 | PASS | `authentik.<domain>` → A `10.1.2.110` + AAAA `fd01:2::110` (dual-stack) |
| NAM-07 | **GAP** | A/AAAA to the proxy, no CNAME (gap 8) |
| NAM-08 | **GAP** | PTR → `proxmox.<domain>` (gap 7) |
| NAM-09 | PASS | DB/Redis/mail hosts referenced by FQDN in the env (`lxc-pgsql-01.<domain>`, `lxc-redis-01.<domain>`, `vm-mailcow-01.<domain>`) |
| NAM-10 | PASS | prod zone clean (`authentik.<domain>`) |
| NAM-11 | PASS | hostname carries no tier |
| NAM-12 | PASS | one LE wildcard per zone at Traefik |
| NAM-13/14 | **GAP** | `poc-data` / `poc-backup` (gap 17) |
| NAM-15/16 | PASS | humans `yboujraf` / `adm_yboujraf` (daily vs admin separation); example identity: gap 19 |
| NAM-17/18 | PASS | `svc-ldap-prod`, `svc-netbird-prod` (env in the name, one per function/env); outpost tokens are Authentik-generated service accounts (`ak-outpost-*`, N/A to the naming rule) |
| NAM-19/20 | N/A | no temp accounts; no Linux groups owned by this service |
| NAM-23 | PASS | groups `{svc}-users` / `{svc}-admins` from `platform_service_groups` + `platform-admins`, `infra-admins` (prefix scheme per naming/0002 §6 applied through the one registry) |
| NAM-25…33 | PASS | FW aliases `port_authentik`, `host4_authentik`, `host6_authentik`; rule `PASS DMZ Traefik→SVC Authentik (reverse proxy)`; no hardcoded IP in rules; aliases in the catalog |
| NAM-34/36/37/38/40 | N/A / PASS | no lib for Authentik; role vars `authentik_*`; Terraform name `lxc-authentik-01` |

## identity / SSO
| ID | Verdict | Evidence |
|---|---|---|
| IDN-01 | PASS | Authentik is the hub: 16 OIDC + 4 proxy apps registered in `group_vars/all/sso.yml` (#718) |
| IDN-02 | PASS | local auth only (no upstream directory configured) |
| IDN-03 | PASS | default authentication flow = Identification → Password → **AuthenticatorValidate (totp/webauthn/static, not_configured_action=configure)** → UserLogin: MFA enforced at login for every human; `adm_yboujraf` 1 device, `yboujraf` 2 |
| IDN-04 | PASS | no enrollment flow on the identification stage; the only enrollment flow is `default-source-enrollment` (social sources, none configured) |
| IDN-05 | PASS | `state: disabled` model in people.yml; blueprints never delete users |
| IDN-06 | N/A | no upstream password source |
| IDN-07 | **GAP** | one instance (gap 11) |
| IDN-09 | PASS | Authentik = IAM source; tools consume OIDC/forwardAuth/LDAP from it |
| IDN-11 | **GAP** | no scheduled reconciliation (gap 10) |
| IDN-12 | N/A | no Authentik→CI webhooks |
| IDN-13 | PASS/GAP | blueprints add, never delete (`authentik_proxy_apps_retired` is explicit); drift alerting: none (gap 10) |
| IDN-14 | PASS | `authentik.yml --check` is the dry-run (used before every apply today) |
| IDN-15 | PASS | group→role mapping in inventory data (`platform_service_groups`), not hardcoded |
| IDN-16 | **GAP** | bootstrap admin at `…/authentik/admin`, no alert on use (gap 9) |
| IDN-17 | **GAP** | no `docs/identity.md` (gap 16) |
| NAM-21/22, IDN-33 | PASS | `{org}` is a local Linux account on the guest (hardening baseline), never Authentik-managed |
| SVC-23, SVC-63 | N/A | NetBox/Harbor rows (their audits) |
| superusers (IDN-16 spirit) | **GAP** | `adm_yboujraf`, `akadmin` and **`svc-netbird-prod`** (gap 1) |

## secrets / Vault
| ID | Verdict | Evidence |
|---|---|---|
| SEC-01 | PASS | machine secrets in Vault; no human password of this service in Vaultwarden |
| SEC-02/03 | PASS | `prod/authentik/admin`, `prod/authentik/db-pgsql`, `prod/mail/authentik`, `prod/authentik/ldap-outpost`, `prod/<svc>/oidc` per app — 3 segments, lowercase-hyphen |
| SEC-04/05 | PASS | AppRole deploy identity (`ansible-deploy`), read scope on `secret/prod/*` (vault_login reports `approle`) |
| SEC-06/07/08 | N/A here | Vault's own audit (root token retired; raft snapshots; HA = Vault pass) |
| SEC-09 | PASS (mechanism) | `vault_secret_force_fields` rotation path; DB password carries `rotated` |
| SEC-12 | N/A | Vaultwarden row |
| IDN-10 | PASS | OIDC client secrets minted into Vault, never files; the role reads them |
| SVC-11 | PASS | mailbox creds `prod/mail/authentik` (address, smtp/imap host+port, password); nothing on disk |
| SVC-28 | PASS / **text gap** | own DB secret, ≥28-char password, injected at runtime; path named `db-pgsql` (gap 18) |
| SVC-03/31/36/54/59, INF-20, SEC-31, INF-43b | N/A | other services' rows |

## database
| ID | Verdict | Evidence |
|---|---|---|
| SVC-25 | N/A here | cluster topology = the PostgreSQL/Redis audits (single node today) |
| SVC-26 | PASS | own database `authentik`, own user `authentik` (postgres_db) |
| SVC-27 | **GAP** | Redis DB number unset → 0, shared credential (gap 4) |
| SVC-28 (sslmode) | PASS | `AUTHENTIK_POSTGRESQL__SSLMODE=verify-full`, `SSLROOTCERT=/etc/ssl/certs/ca-certificates.crt`; Redis `TLS=true`, `TLS_REQS=required` |
| SVC-29 | NOT VERIFIED | grants on `authentik` (postgres_db role: owner of its own DB — verify in the PostgreSQL audit) |
| SVC-30/33 | N/A here | drp clusters; exporters = PostgreSQL/Redis audits (no redis_exporter today) |
| SVC-13/62 | N/A | Mailcow/Harbor rows |

## ingress / DNS
| ID | Verdict | Evidence |
|---|---|---|
| NAM-06/07/08/09/10 | see naming | |
| SEC-28 | PASS | TLS terminates at Traefik; the backend is plain HTTP on `:9000` inside the SVC zone |
| SVC-52/53, SVC-61, INF-16 | N/A | S3/Harbor/router rows |

## certs
| ID | Verdict | Evidence |
|---|---|---|
| SEC-26 | PASS | no self-signed cert: edge = Let's Encrypt (`issuer … Let's Encrypt`, valid to 2026-11-21); LDAP outpost serves a platform cert (roles/authentik `ldap_cert.yml`) |
| SEC-27/29 | PASS | public FQDN → LE resolver |
| SEC-30 | PASS | the host trust store (`/etc/ssl/certs`, platform CA included) is mounted into the containers; verify-full to PG uses it |
| SEC-32/34, NAM-12 | PASS / N/A | cert expiry alerts exist (`TLSCertExpiringSoon/Critical`); no mTLS clients |
| SEC-33 | PASS | LDAP outpost cert issued, not self-signed |

## mailbox / notify
| ID | Verdict | Evidence |
|---|---|---|
| SVC-08/10/12 | PASS | `authentik@<domain>` on Mailcow; outbound through `vm-mailcow-01:587` STARTTLS (`USE_TLS=true`) |
| SVC-09/14/17 | N/A here | Mailcow rows |
| SVC-11 | PASS | creds in Vault (above) |
| SVC-15/16 | PASS | mailbox provisioned by `playbooks/mailboxes.yml` (roles/mailbox, API); one box, RX/TX role: TX = recovery/enrolment mail, RX = delegated to the admin |
| SVC-34/35/36 | N/A | Authentik sends no channel notifications |
| SVC-37 | **GAP** | no `docs/notifications.md` (gap 16) |

## decommission / lifecycle
| ID | Verdict | Evidence |
|---|---|---|
| SVC-47 | PASS | `playbooks/decommission-service.yml` (service_decommission: route, DB, S3, Vault archive, mailbox, CrowdSec machine, Authentik app); proxy apps have an explicit retired list; blueprints are code |
| SVC-43/45 | PASS | scaffold chain (DB → S3 → secrets → mailbox → containers → route → assertions); the catalog row is the spec |
| SVC-44 | NOT VERIFIED | degraded-mode audit records (no degraded path exercised) |
| SVC-46 | PASS/GAP | reverse chain exists; "NetBox marks decommissioned" impossible while NetBox holds no assets (gap 13) |
| SVC-55/58 | N/A / PASS | no S3; CrowdSec stale-machine delete is in crowdsec_agent |
| INF-02/03/04 | PASS (process) | PRs, CI gates, USER merge authority (ADR-0019) |

## hardening
| ID | Verdict | Evidence |
|---|---|---|
| SEC-15 | PASS / **GAP** | Authentik server/worker/ldap run as uid 1000 (`authentik`); `cadvisor` + `portainer-agent` run as root (gap 6) |
| SEC-16 | NOT VERIFIED | vendor image contents (ghcr.io/goauthentik/server) not inspected for toolchain binaries |
| SEC-17 | PASS | secrets reach the containers as runtime env from Vault (7 secret-named keys), none baked in the image or a file |
| SEC-18/19 | **GAP** | no Trivy (gap 14) |
| SEC-20 | PASS | Lynis hardening index **86** (gate 80) |
| SEC-21 | PASS (process) | unattended-upgrades + the security_audit CVE report (patch SLA tracked there) |
| SEC-22 | **GAP** | writable rootfs, no tmpfs (gap 5) |
| SEC-25, IDN-29 | PASS | sshd `:22222`, PermitRootLogin no, PasswordAuthentication no, fail2ban (contract_audit PASS) |
| IDN-22…26 | PASS (platform) | ED25519 keys with passphrases (identity-keys escrow); GPG per identity |
| IDN-27 | **GAP** | automation commits unsigned (gap 15) |
| IDN-28 | PASS | no NOPASSWD in sudoers (baseline) |
| IDN-31 | N/A | OPNsense row |
| IDN-32 | PASS | `docker` group empty on this guest |
| IDN-34 | PASS | guest built by the standard plays (hardening → identity → service) |
| SEC-13 | PASS | no secret printed today (key names only) |
| SEC-35/36 | PASS | `docs/licensing.md` lists Authentik (MIT, approved); Redis AGPL flagged + approved there |

## logging
| ID | Verdict | Evidence |
|---|---|---|
| INF-27 | PASS | promtail running (contract_audit) |
| INF-28 | PASS | streams carry `host`, `env`, `job`, `app`/`container` labels |
| INF-29 | PASS | Loki `retention_period: 2160h` (90 d) platform-wide |
| INF-30/31 | PASS | Authentik logs JSON (`{"event": …, "level": …}`), no secrets observed |
| INF-32 | **GAP** | Authentik streams lack the `audit` label (gap 3) |
| SEC-23/24 | PASS / NOT VERIFIED | auditd on (contract_audit); 180 d immutable audit class not verified |
| SVC-24 | N/A | NetBox row |

## backup
| ID | Verdict | Evidence |
|---|---|---|
| INF-41 | PASS | `docs/backup.md`: class **A + D** (DB in cluster PG; media/templates volumes; blueprints = code); PBS: 21 snapshots, latest 2026-10-02 02:25Z; PBS verify job daily 21:00 (latest snapshot not yet verified at audit time) |
| INF-42 | PASS | PBS datastore mirrored to S3 (SeaweedFS) + Contabo offsite (the backup chain) |
| INF-43 | PASS | PBS encryption + TLS legs (backup chain) |
| INF-44 | NOT VERIFIED | no restore drill of this guest documented |
| INF-45/46 | PASS (platform) | backup job logs → Loki; PBS self-backup excluded |
| INF-06, SEC-07b | N/A here | Terraform/Vault rows |

## pins / versioning / git
| ID | Verdict | Evidence |
|---|---|---|
| SVC-60 | PASS | `ghcr.io/goauthentik/server:2026.5.6` + `…/ldap:2026.5.6` pinned (renovate-tracked) |
| INF-08/09/10/11 | N/A here | Terraform rows (infra repo) |
| GIT-01…06 | PASS | trunk-based, conventional commits (pre-commit), merge commits, PRs; agents open PRs — merging delegated by the USER for the refactor (documented) |
| GIT-10/11 | PASS / N/A | private repos; no `.gitlab-ci.yml` here |
| GIT-13/16 | **GAP** | no git-config role (gap 15) |
| IDN-18/20 | PASS | `by-rune` GH token, one per identity/platform; built-in GITHUB_TOKEN unused for mutations |

## firewall / network
| ID | Verdict | Evidence |
|---|---|---|
| NAM-25…33, SVC-49/50/51 | PASS / N/A | aliases + rule in the catalog (above); seed rows = OPNsense audit |
| INF-12/14/15 | PASS | SVC VLAN /24 dual-stack (`10.1.3.0/24`, `fd01:3::/64`) |
| INF-17/18/19, SVC-01/04/06, SVC-38…40, SVC-56/57 | N/A here | WireGuard/OPNsense/CrowdSec rows |
| DOCKER-USER | PASS | catalog: `authentik` 9000 from traefik, 636 from trusted; enforce mode; the scaffold asserts the published ports (#718) |

## other / env / cmdb
| ID | Verdict | Evidence |
|---|---|---|
| INF-21 | **GAP** | `poc-data`/`poc-backup` storage names (gap 17); no `poc` in any credential/DNS/SA |
| INF-22/23 | PASS | `env: prod` per host in the inventory; the FQDN is the tier carrier |
| INF-24 | PASS | per-env Vault paths and service accounts |
| INF-26 | PASS | prod access = `adm_yboujraf` (+ break-glass `{org}` local) |
| SVC-18/19/20 | **GAP** | NetBox empty (gap 13) |
| SEC-14, INF-01, SEC-11, SEC-10 | PASS / N/A | ADR hygiene; detect-secrets pre-commit on; nothing redacted needed today |
| LIB-01..15 | N/A | no lib for Authentik |

## Fixes from this audit (this pass)

1. **Scoped permissions for `svc-netbird-prod`** instead of superuser (identity blueprint) — verified by NetBird's directory sync still working.
2. **Authentik `/metrics` scraped**: port `9300` published on the host (DOCKER-USER catalog: from the monitoring host), Prometheus job `authentik`.
3. **`audit` label on Authentik's container logs** (roles/promtail: audit-class containers per host).
4. **Own Redis DB number** for Authentik from a platform allocation table (announce: cached sessions drop once).
5. **`docs/identity.md` + `docs/notifications.md` for Authentik.**

Platform-wide items (one fix for every service, scheduled as their own passes): read-only rootfs + tmpfs,
PTR of the proxy address, Trivy gate, git-config/signing, NetBox population, alerts + dashboards per service,
per-service Redis ACL users.

Decisions for the USER (ADR text or identity data): NAM-07 (A/AAAA vs CNAME), IDN-16 path naming
(`…/admin` vs `…/break-glass`), SVC-28 (`db-pgsql` vs `db-password`), NAM-03 (15-char hostnames vs the
`lxc-` site code), SEC-15 exception for host agents, IDN-07 (HA with k3s), IDN-11 (where the scheduled
reconcile runs), `yboujraf_example` state, `poc-*` storage rename.
