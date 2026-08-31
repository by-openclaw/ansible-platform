<!-- Header: ADR-derived compliance checklist. Generated 2026-08-31 from
     doc-platform-core/docs/adr/ (33 ADRs, 7 scopes) as the per-service audit
     instrument. Purpose: make service compliance complete-by-construction —
     every normative clause (MUST/SHALL/REQUIRED/MANDATORY/never/always/only) is
     a numbered, testable check with its ADR reference. Re-audit EVERY service
     against this, not a hand-derived subset. IDs are stable/traceable. -->

# ADR Compliance Checklist — per-service audit instrument

> **Why this exists:** the earlier per-service audit used a hand-derived R1–R16
> list, so ADR clauses that weren't in that list (svc naming, per-service
> mailbox, decommission absent-path, DB verify-full, SSO-everywhere) slipped
> through and only surfaced when the owner noticed. This checklist is derived
> **directly and exhaustively from the ADRs** so nothing depends on memory.
> Source: `doc-platform-core/docs/adr/`. Verify each item live before acting.

Each row: **ID** · testable check · ADR source · category. Audit every deployed
service and its Ansible role against the full list.

## naming
| ID | Check | Source |
|---|---|---|
| NAM-01 | Every host/VM/LXC has an authoritative NetBox `name`; TF/Ansible/monitoring read it, never invent/override locally | naming/0001 §1 |
| NAM-02 | Asset name carries no metadata (env/role/site/tenant/IP/tags) — those live in NetBox fields | naming/0001 §1,§10 |
| NAM-03 | Hostname ≤ 15 chars | naming/0001 §2 |
| NAM-04 | Hostname `{site}-{service}-{seq:02d}`, lowercase hyphen, no underscores | naming/0001 §3 |
| NAM-05 | Proxmox VMs/LXCs use site code `vm` (not `br`) | naming/0001 §4 |
| NAM-11 | Hostname has no env tier / role beyond service code / redundancy position / physical site | naming/0001 §10 |
| NAM-13 | Token `poc` in no host/storage name | naming/0001 §4.1 |
| NAM-14 | PVE storage IDs env/site-free `{content}-{backend}` (data-zfs/iso-nfs/pbs-s3) | naming/0001 §4.1 |
| NAM-15 | Humans `{handle}` / `adm_{handle}`; handle lowercase `[a-z0-9]+`, immutable | naming/0002 §2 |
| NAM-17 | **Service accounts `svc-{function}-{env}`** — env baked into the name | naming/0002 §3 |
| NAM-18 | One service account per (function,env); credential never shared across envs | naming/0002 §3 |
| NAM-19 | Temp accounts `tmp-{purpose}-{env}` with a mandatory expiry | naming/0002 §4 |
| NAM-20 | Linux groups bare names (no `grp-`), env-agnostic | naming/0002 §5 |
| NAM-23 | Authentik groups `{prefix}{scope}-{role}`, prefix ∈ {tool-,svc-,prj-,org-} | naming/0002 §6 |
| NAM-34 | Repos `{type}-{product}`, lowercase hyphen; one per (type,product) | naming/0004 §1 |
| NAM-36 | Python package = product (hyphen for pip / underscore for import); no lib-/by- prefix | naming/0004 §2 |
| NAM-37 | Ansible modules `{product}_{domain}_{entity}`, thin wrapper over one manager | naming/0004 §5 |
| NAM-38 | Ansible vars `{short}_{scope}_{name}` snake_case; entity-list vars plural | naming/0004 §7 |
| NAM-40 | Terraform `name` = `{site}-{service}-{seq:02d}` | naming/0004 §9 |

## identity / SSO
| ID | Check | Source |
|---|---|---|
| IDN-01 | **Every tool authenticates through Authentik (SSO)** — the only mandatory hub | identity/0001 |
| IDN-02 | Authentik local auth works when upstream directory is down (upstream inbound-only) | identity/0001 |
| IDN-03 | MFA (TOTP) enforced in Authentik | identity/0001 |
| IDN-04 | Self-service signup disabled; admin creates → enrollment link | identity/0001 |
| IDN-05 | Account lifecycle = disable-never-delete | identity/0001; identity/0002 |
| IDN-06 | Passwords never sync from upstream | identity/0001 |
| IDN-07 | Authentik HA: 2 active/active | identity/0001 |
| IDN-09 | Authentik is IAM source of truth; tools downstream, not hand-configured | identity/0002 |
| IDN-11 | Tool-UI change = break-glass only; 4-hour reconciliation cron corrects drift | identity/0002 |
| IDN-12 | Authentik→CI webhooks HMAC-SHA256 (Vault secret), replay-reject >5min, TLS, trigger-only | identity/0002 |
| IDN-13 | Provisioning never auto-deletes; drift corrected silently, always alerted | identity/0002 |
| IDN-14 | identity-sync supports `--check`; dry-run before any prod sync | identity/0002 |
| IDN-15 | Group→role mapping in `roles/identity-sync/vars/{tool}-mapping.yml`, never hardcoded | identity/0002 |
| IDN-16 | Bootstrap admin creds → Vault then rotated; break-glass `secret/{env}/{tool}/break-glass`, alert on use | identity/0002 |
| IDN-17 | Each tool has `docs/identity.md` (6 required items) | identity/0002 |
| NAM-16 | `adm_*` for admin tasks only; daily work uses standard account | naming/0002 §2 |
| NAM-21 | Only `{org}` (break-glass) may use password auth; all others key-only always | naming/0002 §5.1 |
| NAM-22 | `break-glass` group contains `{org}` only | naming/0002 §5.2 |
| IDN-33 | `{org}`/break-glass never Authentik-managed, never deleted (local `/etc/passwd`) | identity/0004 §1,§10 |
| SVC-23 | NetBox uses Authentik OIDC; break-glass local admin in Vault | services/0003 §7 |
| SVC-63 | Harbor Authentik OIDC (`harbor-admins`→admins); sealed local admin; CI via robot | services/0011 §3 |

## secrets / Vault
| ID | Check | Source |
|---|---|---|
| SEC-01 | Vault (machines) vs Vaultwarden (humans) hard boundary — no secret in both | security/0001 |
| SEC-02 | Every Vault path `secret/{env}/{service}/{key}` — 3 segments, env explicit, no root paths | security/0001 |
| SEC-03 | Vault keys lowercase-hyphen; one credential = one KV value, never split | security/0001 |
| SEC-04 | Per-service Vault policy scoped to own prefix; least-privilege (read default) | security/0001 |
| SEC-05 | Service accounts auth to Vault via AppRole (per-env role_id + wrapped secret_id) | security/0001 |
| SEC-06 | Root token revoked after init; unseal keys off-platform in cold storage | security/0001; identity/0002 |
| SEC-07 | Vault audit logging enabled → Loki (every read/write/policy-change) | security/0001; infra/0006 |
| SEC-08 | Vault HA (2 instances) before prod cut-over | security/0001 |
| SEC-09 | Static creds rotated on incident + schedule (key + passphrase + Vault record together) | security/0001 |
| SEC-12 | Vaultwarden: random 24+ char, 2FA mandatory, master password nowhere else | security/0001 |
| IDN-10 | Vault = credentials source of truth (API tokens, client secrets, SSH passphrases) | identity/0002; identity/0004 §11 |
| SVC-03 | OPNsense API key in Vault `secret/{env}/opnsense/svc-rune-api-key` | services/0001 |
| SVC-11 | All mailbox IMAP/SMTP creds in Vault `secret/{env}/mail/{tool}`; none on disk | services/0002 |
| SVC-28 | Per-service DB creds in Vault `secret/{env}/{service}/db-password`, ≥32 chars, runtime-injected | services/0004 |
| SVC-31 | DB break-glass superuser in Vault, audited on read, rotated after use | services/0004 |
| SVC-36 | Notification creds only in Vault (Graph/Discord/Mailcow) | services/0005 |
| SVC-54 | S3 creds: generate once → fabric → Vault mirror; per-service scoped | services/0009 |
| SVC-59 | CrowdSec bouncer keys/tokens in Vault `prod/crowdsec/*` | services/0010 |
| INF-20 | WireGuard server private key in Vault; only peer public keys in git | infra/0004 §8 |
| SEC-31 | step-ca root key sealed in Vault, never on host FS after setup | security/0004 |
| INF-43b | Backup encryption keys in Vault, never leave unencrypted | infra/0008 |

## database
| ID | Check | Source |
|---|---|---|
| SVC-25 | PostgreSQL (Patroni 3-node) + Redis (Sentinel) clustered for all tiers above dev | services/0004 |
| SVC-26 | Each service own database + own dedicated user scoped to it only | services/0004 |
| SVC-27 | Each Redis consumer own DB number/prefix; cache/session/queue only | services/0004 |
| SVC-29 | Least-privilege grants (CONNECT+USAGE+CRUD own schema); no GRANT ALL | services/0004 |
| SVC-30 | drp = its own PG+Redis clusters (restore-populated), not prod replicas | services/0004 |
| SVC-33 | postgres_exporter + redis_exporter exposed | services/0004 |
| SVC-13 | Mailcow uses its internal MariaDB/Redis, NOT the shared cluster | services/0002; services/0004 |
| SVC-62 | **Harbor metadata in cluster PG (`harbor` DB) `sslmode=verify-full`**; blobs S3; queue bundled Redis | services/0011 §2 |

## ingress / DNS
| ID | Check | Source |
|---|---|---|
| NAM-06 | Every FQDN + service URL resolves both A + AAAA (no single-family) | naming/0001 §6.1; infra/0004 §9 |
| NAM-07 | Service URLs CNAME to the proxy; direct A+AAAA only w/o proxy; no CNAME at apex | naming/0001 §6.1 |
| NAM-08 | PTR (in-addr.arpa + ip6.arpa) for every asset → asset FQDN | naming/0001 §6.1 |
| NAM-09 | No hardcoded IPs in app config — reference FQDNs | naming/0001 §6.1 |
| NAM-10 | Prod DNS zone clean (no env sub-domain); non-prod injects env sub-domain | naming/0001 §7 |
| SEC-28 | Traefik is the single TLS termination point; no per-service/app TLS | security/0004 |
| SVC-52 | SeaweedFS is the S3 engine; MinIO decommissioned, never redeployed | services/0009 |
| SVC-53 | One bucket-set + one scoped S3 identity per service; no shared/anon buckets | services/0009 |
| SVC-61 | Harbor at `harbor.{domain}`, TLS at Traefik, internal-only, pinned release | services/0011 |
| INF-16 | OPNsense the only router; inter-VNet traffic traverses OPNsense | infra/0004 §6 |

## certs
| ID | Check | Source |
|---|---|---|
| SEC-26 | No self-signed TLS anywhere, any service/device | security/0004 |
| SEC-27 | CA chosen mechanically: internal/IANA-reserved → step-ca; public FQDN → Let's Encrypt | security/0004 |
| SEC-29 | Internal UIs use `stepca` resolver; public use `letsencrypt` | security/0004 |
| SEC-30 | Every VM cloud-init writes step-ca root CA to trust store; `ca-trust` role is a pre-dep of every VM playbook | security/0004 |
| SEC-32 | Root CA expiry monitored, alert 90 days before | security/0004 |
| SEC-33 | Devices terminating own TLS get a cert via `cert-issue` (LE/step-ca), never self-signed | security/0004 |
| SEC-34 | Client/mTLS certs from step-ca only | security/0004 |
| NAM-12 | One wildcard TLS cert per DNS zone | naming/0001 §8; security/0004 |

## mailbox / notify
| ID | Check | Source |
|---|---|---|
| SVC-08 | Every tool mailbox on Mailcow, never Exchange | services/0002 |
| SVC-09 | `catchall@{domain}` is a real Mailcow mailbox (mandatory) | services/0002 |
| SVC-10 | Outbound mail always through Mailcow SMTP | services/0002 |
| SVC-12 | TLS on every mail leg (IMAP/SSL, SMTP STARTTLS, relay TLS) | services/0002 |
| SVC-14 | Hybrid: Mailcow "Relay non-existing mailboxes only" set | services/0002 |
| SVC-15 | Mailbox creation via Ansible against Mailcow API, not manual | services/0002 |
| SVC-16 | **Each tool exactly one owner/purpose/mailbox with a defined RX/TX role** | services/0002 |
| SVC-17 | DKIM/SPF/DMARC per domain via Mailcow API by Ansible | services/0002 |
| SVC-34 | Notifications one-way tool→channel; deep link to source; none default to #general | services/0005 |
| SVC-35 | Standard template; `Who:` never empty (use "system") | services/0005 |
| SVC-37 | Each tool has `docs/notifications.md` (5 items) | services/0005 |

## decommission / lifecycle
| ID | Check | Source |
|---|---|---|
| SVC-47 | **Every object class has BOTH a present and an absent path** — no absent-path = violation | services/0007 §7.1 |
| SVC-43 | Provisioning runs the fixed 8-step chain in order; idempotent; halt+rollback on failure | services/0007 |
| SVC-44 | Every degraded-mode fallback emits an audit record to RAID + Loki | services/0007 |
| SVC-45 | Workload spec = single source of truth; no invented fields | services/0007 |
| SVC-46 | Decommission = same 8 steps reversed (state=absent); NetBox marks decommissioned, never delete | services/0007 |
| SVC-55 | S3 decommission removes bucket (archive-before-destroy) + identity via catalog | services/0009 |
| SVC-58 | On guest rebuild, delete stale CrowdSec machine at LAPI before re-enrol | services/0010 |
| INF-02 | Strict sequential layers; no layer starts until previous documented/tested/signed by @yboujraf | infra/0002 |
| INF-03 | No Layer-5 service before Layers 1–4 complete | infra/0002 |
| INF-04 | Agent detecting a gate violation halts + raises RAID; never "fix and move on"; agents never sign off/merge/bypass | infra/0002 |

## hardening
| ID | Check | Source |
|---|---|---|
| SEC-15 | Every container/service runs non-root (image `USER` before ENTRYPOINT; host = dedicated system user) | security/0003 §1 |
| SEC-16 | Images exclude build toolchain (gcc/make/curl/wget/nc/nmap) unless required; slim/distroless | security/0003 §2 |
| SEC-17 | No plaintext secrets in images/env; injected at runtime | security/0003 §3 |
| SEC-18 | Trivy on every PR; gate blocks on zero-critical + zero-high | security/0003 §4 |
| SEC-19 | `.trivyignore` suppressions need per-entry justification + expiry | security/0003 §4 |
| SEC-20 | Lynis on every Linux host via `hardening`; score <80 fails the play | security/0003 §5 |
| SEC-21 | CVE patch SLA 72h/7d/30d/90d (crit/high/med/low) | security/0003 §6 |
| SEC-22 | Container rootfs read-only + tmpfs for /tmp,/run; state on named volumes | security/0003 §7 |
| SEC-25 | SSH: PermitRootLogin no (break-glass Match), port 22222, fail2ban + OOB whitelist | security/0003 §9; identity/0004 §5 |
| IDN-22 | SSH keys ED25519 only | identity/0004 §2 |
| IDN-23 | Every SSH private key has a passphrase; empty-passphrase forbidden | identity/0004 §2 |
| IDN-24 | One ED25519 key pair per identity, comment `{username}@{domain}` | identity/0004 §2 |
| IDN-25 | SSH keys rotated every 365 days (Vault key-age), alert 30 days before | identity/0004 §2 |
| IDN-26 | GPG EdDSA, passphrase, 365-day expiry, 30-day alert | identity/0004 §3 |
| IDN-27 | Git commit + tag signing enforced | identity/0004 §3; git/0003 |
| IDN-28 | NOPASSWD / !authenticate forbidden in sudoers | identity/0004 §4 |
| IDN-29 | PasswordAuthentication no globally; re-enabled only via Match for break-glass from OOB CIDR | identity/0004 §5 |
| IDN-31 | OPNsense users `shell=/bin/sh` (default "none" kills SSH) | identity/0004 §6 |
| IDN-32 | `docker` group only on Docker hosts; only `svc-rune`; `{org}` never in it | identity/0004 §7 |
| IDN-34 | Every new VM/LXC runs the 6-role provisioning playbook; no ad-hoc user/key | identity/0004 §9 |
| SEC-13 | Secret files never cat/echo'd to terminal | security/0001; identity/0004 §11 |
| SEC-35 | Every tool has `docs/licensing.md` (SPDX ID + URL + version + last-reviewed + BoM) | security/0005 |
| SEC-36 | Flagged licenses (BUSL/SSPL/AGPL/Elastic-2.0/Commons Clause/proprietary) need written @yboujraf approval | security/0005 |

## logging
| ID | Check | Source |
|---|---|---|
| INF-27 | **Every host runs Promtail — no exceptions** | infra/0006 |
| INF-28 | Promtail labels host/service/env/scope from NetBox metadata | infra/0006 |
| INF-29 | Log retention ≥30d default; audit services (Vault/Authentik/GitLab/OPNsense) ≥90d | infra/0006 |
| INF-30 | No credentials/PII/secrets in any log stream (enforced at emitter) | infra/0006 |
| INF-31 | Structured JSON logs (free-text only where impossible) | infra/0006 |
| INF-32 | Security streams (Vault audit, sshd/PAM, fail2ban, OPNsense, Traefik) → Loki with `audit` label | infra/0006 |
| SEC-23 | auditd on all VMs; sshd/PAM sessions logged; both → Loki | security/0003 §8 |
| SEC-24 | Audit log retention 180d; write-once/immutable from platform SAs | security/0003 §8 |
| INF-33 | Every service exposes `/metrics` (deploy gate) | infra/0007 |
| INF-34 | node_exporter on every VM | infra/0007 |
| INF-35 | Every service ≥3 alerts (service-down, saturation, app SLI) | infra/0007 |
| INF-36 | No alert without an action; critical links a runbook; silences time-bound | infra/0007 |
| INF-38 | Grafana dashboards as code; UI changes break-glass, reconciled in a day | infra/0007 |
| INF-39 | Every service ≥1 dashboard + ≥1 alert (deploy gate) | infra/0007 |
| SVC-24 | NetBox drift logged to Loki with `drift` tag | services/0003 |

## backup
| ID | Check | Source |
|---|---|---|
| INF-41 | Every stateful service: one backup class + `docs/backup.md` + verified first backup before prod | infra/0008 |
| INF-42 | Off-site mandatory for prod/drp; 3-2-1 target | infra/0008 |
| INF-43 | Backup at-rest encrypted (keys in Vault); in-transit TLS every leg | infra/0008 |
| INF-44 | Restore drills on cadence; ≥1 documented drill per tier per year | infra/0008 |
| INF-45 | Backup run logs → Loki `audit` label, 90d retention | infra/0008 |
| INF-46 | PBS never self-backs into its own S3 (DR→NFS); OPNsense freeze-fs-on-backup=0 | infra/0008 |
| INF-06 | Terraform state backed up to NAS after every apply/destroy | infra/0003 |
| SEC-07b | Vault DR = daily raft snapshot → NFS + S3 + controller | infra/0008; security/0001 |

## pins / versioning / git
| ID | Check | Source |
|---|---|---|
| SVC-60 | Harbor from a pinned release — never `:latest` | services/0011 |
| INF-08 | Terraform + every provider pinned (`~>`); lock committed | infra/0003 |
| INF-09 | Provider upgrades are their own PRs | infra/0003 |
| INF-10 | TF CI: fmt-check+validate+tflint+checkov before plan; apply manual post-merge | infra/0003 |
| INF-11 | No tfstate in git; state = secret-equivalent | infra/0003 |
| GIT-01 | Trunk-based: `main` only long-lived branch | git/0001 |
| GIT-02 | Conventional Commits enforced | git/0001 |
| GIT-03 | Merge `--no-ff`; squash + rebase merge disabled | git/0001 |
| GIT-04 | No direct/force push to main ever | git/0001 |
| GIT-05 | Every PR ≥1 human approval; agent approvals don't count | git/0001 |
| GIT-06 | Agents open PRs, never merge; @yboujraf sole merge authority | git/0001 |
| GIT-10 | GitHub repos all private | git/0002 |
| GIT-11 | `.gitlab-ci.yml` includes ci-templates by reference, never copy-paste | git/0002 |
| GIT-13 | System /etc/gitconfig invariants (sslVerify on, merge.ff=false, fsckObjects, defaultBranch=main) | git/0003 |
| GIT-16 | git-config applied by the `git-config` role on every git-using VM/LXC | git/0003 |
| IDN-18 | CI tokens `{IDENTITY}_{PLATFORM}_TOKEN`; one per identity per platform | identity/0003 |
| IDN-20 | Built-in GITHUB_TOKEN read-only, never mutations | identity/0003 |
| SVC-49 | OPNsense seed from `build-seed.py`, never a saved backup; secrets at render time | services/0008 |

## firewall / network
| ID | Check | Source |
|---|---|---|
| NAM-25 | Atomic aliases `net_/host_/port_/url_` prefixes, lowercase underscore | naming/0003 §1 |
| NAM-26 | One atomic alias per concept — duplicates are a violation | naming/0003 §1 |
| NAM-27 | No hardcoded IPs/ports in rule fields — always an alias | naming/0003 §3 |
| NAM-28 | No auto-generated/person/device alias names | naming/0003 §3 |
| NAM-29 | Group alias needs a one-sentence semantic justification in its description | naming/0003 §2 |
| NAM-30 | Rule descriptions `{ACTION} {src}→{dst} {service}` | naming/0003 §4 |
| NAM-31 | Hardening role removes rules with `BOOTSTRAP-TEMP` in description | naming/0003 §5 |
| NAM-33 | Aliases version-controlled in the Ansible OPNsense role; none created in UI | naming/0003 §7 |
| INF-12 | VLAN subnets /24 minimum | infra/0004 §1 |
| INF-14 | VLAN 1 never used; reserved 1–999 unallocated | infra/0004 §2 |
| INF-15 | Every VLAN dual-stack (v4 + v6 ULA) | infra/0004 §9 |
| INF-17 | WireGuard one peer per device (never per user), `peer-{owner}-{device}` | infra/0004 §8 |
| INF-18 | WireGuard keypair per device; private key never leaves device | infra/0004 §8 |
| INF-19 | No device = no peer; lost/decommissioned device's peer removed immediately | infra/0004 §8 |
| SVC-01 | Terraform owns OPNsense VM shell only, never OS/firewall config | services/0001 |
| SVC-04 | After Phase 1, Ansible owns all OPNsense config; no hardcoded VLAN/subnet/zone | services/0001 |
| SVC-06 | Manual OPNsense UI change = drift incident → update role, check-mode, re-apply | services/0001 |
| SVC-38 | Suricata IDS alert-only at deploy on WAN1 (not IPS/drop) | services/0006 |
| SVC-39 | IDS→IPS promotion gated (≥30d alert-only + FP<5% + ADR amendment) | services/0006 |
| SVC-40 | Only TTL service edits `host_internet_request`; every change → Loki+RAID (max 4h/24h) | services/0006 |
| SVC-50 | Re-run Ansible MVC after any OPNsense config import (drift rule) | services/0008 |
| SVC-51 | Fresh FW reaches full state via seed + Ansible MVC, proven by `fw_verify_health.py` green twice | services/0008 |
| SVC-56 | CrowdSec central LAPI on lxc-crowdsec-01; agents on every guest (Vault reg token) | services/0010 |
| SVC-57 | CrowdSec enforcement central (OPNsense + Traefik bouncers); no inline Suricata IPS | services/0010 |

## other / env / cmdb
| ID | Check | Source |
|---|---|---|
| INF-21 | Six tiers only (dev/test/staging/acc/prod/drp); `poc` in NO asset/credential/DNS/secret/SA name | infra/0005 |
| INF-22 | prod always explicit; every resource carries its env tier label | infra/0005 |
| INF-23 | Env tier per-asset (NetBox/TF var/host_var), not derived from Proxmox node | infra/0005 |
| INF-24 | Credentials per-environment; a dev token cannot reach prod | infra/0005 |
| INF-26 | prod asset access limited to `adm_*` (max 2–3 per asset) | infra/0005 |
| SVC-18 | NetBox holds every managed asset; may reference a Vault path but never a secret value | services/0003 |
| SVC-19 | Every asset carries NetBox fields: env, role, service_url, prometheus_job, vault_path_prefix, backup_class, owner | services/0003 |
| SVC-20 | NetBox `role` is a closed list; new roles by ADR amendment only | services/0003 |
| SEC-14 | Every ADR has a `CISO mapping` section (or N/A) | security/0002 |
| INF-01 | ADRs always Markdown; diagrams have source + rendered committed; no SaaS docs tools | infra/0001 |
| SEC-11 | `detect-secrets` pre-commit on every repo, blocks leaks | security/0001 |
| SEC-10 | Secrets in shared text redacted `<REDACTED:{type}>` | security/0001 |
| LIB-01..15 | lib-* repos follow the Python library design standard (layering, DI creds, async, _match_keys, _validators, try/except/log/raise, REDACT_FIELDS, tests, gates) | lib/python/0001 |

## AUDIT-CRITICAL, easily-missed (check these first, every service)
1. **NAM-17 / INF-22** — service accounts `svc-{function}-{env}` (env in the name); every resource carries its tier; `poc` nowhere (INF-21).
2. **SVC-16 + SVC-09** — per-service mailbox with an explicit RX/TX role; real `catchall@{domain}` mailbox.
3. **SVC-47** — every object class needs BOTH present and absent (decommission) paths.
4. **SVC-62 + SVC-26** — per-service DB + dedicated least-priv user; DB connections `sslmode=verify-full`.
5. **IDN-01 / SVC-23 / SVC-63** — SSO via Authentik mandatory; break-glass local admin only, in Vault.
6. **SVC-60 + INF-08** — no `:latest`; TF + providers pinned with committed lock.
7. **NAM-06 + NAM-08** — dual-stack DNS (A+AAAA) and PTR (v4+v6) for every asset.
8. **SEC-30** — step-ca root CA in every VM trust store via the `ca-trust` pre-dep role.
9. **INF-33 + INF-39** — `/metrics` + ≥1 dashboard + ≥1 alert are deploy gates.
10. **INF-41** — backup class + runbook + verified first backup before prod; off-site for prod/drp.
11. **SEC-15 + SEC-22** — containers non-root + read-only rootfs + tmpfs.
12. **IDN-31** — OPNsense accounts `shell=/bin/sh`.
13. **SEC-19** — Trivy suppressions need per-entry justification + expiry.
14. **NAM-27 + SVC-50** — no hardcoded IPs/ports in OPNsense rules; re-run MVC after any import.
15. **IDN-05 / IDN-29 / IDN-23** — disable-never-delete; PasswordAuthentication no except break-glass OOB; no empty-passphrase keys.
