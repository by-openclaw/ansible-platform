<!--
  ADR compliance audit — Nextcloud. Instrument: docs/audits/adr-compliance-checklist.md (209 checks).
  Method: roles/contract_audit (automated, PASS=11 FAIL=0 SKIP=22) + manual walk on the live guest.
-->
# ADR compliance audit — Nextcloud (2026-10-02)

**Service:** `nextcloud` (`roles/nextcloud`, `playbooks/nextcloud.yml`) on `lxc-nextcloud-01` (ct 503) — `nextcloud.<domain>`, public, OIDC, shared PG, image `nextcloud:34.0.4-apache` (web + cron), 16 apps pinned with checksums.
**Verdicts:** **PASS** (evidence seen) · **GAP** (evidence contradicts the ADR) · **N/A** · **NOT VERIFIED**. Each gap names where it is fixed and who decides: **FIX** = code within the ADRs (this pass) · **PLATFORM** = one fix covers every service (own pass) · **PROPOSE** = the ADR text or owner data must change (owner decision).
Rows identical to the Authentik audit (same `base`/`docker`/`hardening`/`promtail` roles on an LXC guest) carry the same verdict and say so.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | INF-41, INF-42 | **Every user file exists exactly once**: primary storage is the S3 bucket `nextcloud-data` at an external provider (`eu2.contabostorage.com`); no sync, replica or export of that bucket exists anywhere (PBS holds the config volume — ct 503: 21 snapshots, latest 2026-10-02T01:39Z, ~14.5 GB; PG is dumped daily by `roles/postgresql`). Provider-side loss or a credential compromise = total loss of the files. | **FIXED** — #731: `seaweedfs_mirrors` (pinned rclone, scoped identity, Vault creds, 30-day trash), first run 108/108 objects equal, daily 03:30; the provider is one definition (`platform_external_s3`) read by roles/nextcloud too |
| 2 | SEC-01 (spirit), INF-42 | **Files rest in cleartext at a third party**: the `encryption` app is disabled, so the external bucket holds readable user data. | **PROPOSE → doc-platform-core #69** — services/0009 §4: external provider = interim (mirrored + application-encrypted or registered risk), platform S3 the target primary; recommended: register the risk, schedule the move |
| 3 | SEC-15 | `nextcloud` and `nextcloud-cron` start as **root** (`user: ''`, Apache master PID 1 root, 10 workers `www-data`; the vendor entrypoint chowns then drops) — the ADR forbids root processes and says `--user` is not a workaround. | **PROPOSE → doc-platform-core #68 (§1 clause)** + register entry OH-3 in #724 (master root, 10 workers `www-data`; rootless variant when upstream ships one) |
| 4 | INF-27, INF-32, SEC (IPS) | The application log (`nextcloud.log`, 2.2 MB in the `nextcloud-app` volume, `log_type` unset = file) is **not shipped to Loki** (0 `reqId` lines) and **not read by CrowdSec** (host agent: `linux`/`postfix`/`sshd` only; `crowdsecurity/nextcloud` disabled on the engine; no acquisition). Container stdout is shipped (402 lines/h). | **FIXED** — #730 + #732: promtail job `nextcloud_app` with `audit="true"` (traverse ACL on /var/lib/docker), CrowdSec agent `file` datasource + `crowdsecurity/nextcloud`; probe: 3 failed logins → 3 lines in Loki, 3/3 parsed by `nextcloud-logs`, whitelisted source → no ban |
| 5 | INF-35 | **No application metrics**: no exporter, `serverinfo` token unset; only node/cadvisor/blackbox (all `up`). | **FIXED** — #729: serverinfo token in Vault, `nextcloud-exporter` sidecar, `metrics_port: 9205` → Prometheus job `nextcloud` up, `nextcloud_up` = 1 |
| 6 | SVC-27 | Redis `dbindex` unset (DB 0 shared) although the allocation table reserves **3**. | **FIXED** — #728: `redis dbindex` = 3 (allocation table), fingerprint input |
| 7 | SVC (health) | 19 **missing optional DB indices** (taskprocessing, mail, polls, tables) reported by `occ setupchecks`. | **FIXED** — #728: `occ db:add-missing-indices` in post-install; setupchecks no longer lists missing indices |
| 8 | SVC (health) | Talk: HPB **version mismatch** (`2.1.1~docker`, "missing features: changed-users") and **Client Push not installed**. | **FIX in the `collab` walk** (next service) |
| 9 | IDN-13 (scope) | All 23 IdP groups are provisioned into Nextcloud (`gitlab-admins`, `harbor-users`, …), not only `nextcloud-*`/`admin`. | **PLATFORM** — scope the group claim per application (Authentik property mapping) |
| 10 | IDN-16 | Break-glass `admin` (local, no MFA) at `secret/{env}/nextcloud/admin`, no alert on use. | **PROPOSE** — doc-platform-core #65 (A); alert = Vault audit pass |
| 11 | SEC-22 | Writable rootfs, no tmpfs (both containers). | **PLATFORM** — scaffold read-only + tmpfs pass (Authentik gap 5) |
| 12 | SEC-23 | **auditd is inactive on this guest — and on `lxc-authentik-01`** (unprivileged LXC: the kernel audit subsystem is not available to the container; the hardening role deploys rules nobody consumes). The Authentik record's SEC-23 "PASS" is corrected by this finding. | **PLATFORM** — audit at the hypervisor (host auditd covers every container) or Wazuh syscheck; hardening walk |
| 13 | IDN-17, SVC-37 | No `docs/services/nextcloud.md` (identity + notifications). | **FIXED** — `docs/services/nextcloud.md` (#727) |
| 14 | NAM-03 | 16-character hostname (`lxc-nextcloud-01`). | note — platform decision (Authentik record) |

## naming
| ID | Verdict | Evidence |
|---|---|---|
| NAM-01/02 | GAP (platform) | NetBox holds no assets (Authentik gap 13) |
| NAM-03 | note | `lxc-nextcloud-01` = 16 chars (gap 14) |
| NAM-04–06 | PASS | `lxc-nextcloud-01.<domain>` A/AAAA = `10.1.3.170` / `fd01:3::170`; service URL `nextcloud.<domain>` |
| NAM-07 | GAP (platform) | A/AAAA to the proxy — doc-platform-core #67 |
| NAM-08 | PASS | PTR of `10.1.3.170` = asset FQDN (first override); the proxy address reverses to `lxc-traefik-01` since #723 |
| NAM-13/14 | GAP (owner) | `poc-data`/`poc-backup` storage names (Authentik gap 17) |
| NAM-15–18 | PASS | humans `yboujraf`/`adm_yboujraf` separated; the only local account is the break-glass `admin` |

## identity / SSO
| ID | Verdict | Evidence |
|---|---|---|
| IDN-01/02 | PASS | OIDC via `user_oidc`, provider `authentik`, registered in `group_vars/all/sso.yml` (`restrict_to_group: nextcloud-users`, `admin_source_group → admin`) |
| IDN-03 | PASS | 3 users; `admin` (break-glass) + `adm_yboujraf` in `admin`; no example identity present here |
| IDN-05 | PASS | MFA enforced at the IdP; Nextcloud-side 2FA not enforced (ℹ) — only the local `admin` is outside the IdP (gap 10) |
| IDN-07 | N/A | single-instance app behind Traefik; HA = platform (Authentik gap 11) |
| IDN-11/13 | GAP (platform) | no scheduled reconcile (#65 B); group scope gap 9 |
| IDN-16 | GAP | gap 10 |
| IDN-17 | GAP → fixed | `docs/services/nextcloud.md` created with this audit |
| IDN-27 | GAP (platform) | unsigned automation commits (Authentik gap 15) |

## secrets / Vault
| ID | Verdict | Evidence |
|---|---|---|
| SEC-01–05 | PASS | `secret/{env}/nextcloud/{admin, db-pgsql, oidc}` + shared `redis` and S3 credentials read by `vault_secret` (deploy AppRole); no file secret; no secret printed today |
| SEC-06 | PASS | AppRole model; root token retired |
| SEC-07 | PASS | PG `sslmode=verify-full` (contract_audit), Redis `rediss://` with `verify_peer` + CA |

## database
| ID | Verdict | Evidence |
|---|---|---|
| SVC-26 | PASS | own database/role on the shared cluster (`postgres_db`), owner-only |
| SVC-27 | GAP | Redis dbindex unset (gap 6) |
| SVC-28 | PASS | `db-pgsql` document (services/0004 as amended 2026-09-29) |
| SVC-29 | PASS | credentials minted by `postgres_db`, consumed by name |

## ingress / DNS / certs
| ID | Verdict | Evidence |
|---|---|---|
| SVC-01–04 | PASS | Traefik route (public, rate-limit 300/600 per IP, security headers → setupchecks "HTTP headers ✓"), CrowdSec bouncer alive at Traefik, `trusted_proxies = 10.1.2.110 172.17.0.0/16`, `overwriteprotocol https` |
| SEC-08–10 | PASS | wildcard certificate at Traefik; `/etc/ssl/certs` mounted read-only for outbound trust |
| SVC-05 | PASS | `.well-known` + WebDAV + OCS checks ✓ |

## mailbox / notify
| ID | Verdict | Evidence |
|---|---|---|
| SVC-33–36 | PASS | SMTP `vm-mailcow-01.<domain>:587` STARTTLS, from `nextcloud@<domain>`; setupchecks "Mail Transport ✓ / performance ✓"; Mail app provisioning for SSO users |
| SVC-37 | GAP → fixed | notifications section in `docs/services/nextcloud.md` |

## hardening
| ID | Verdict | Evidence |
|---|---|---|
| SEC-15 | **GAP** | root entrypoint (gap 3); `cadvisor`/`portainer-agent` as in the register (#724) |
| SEC-16 | NOT VERIFIED | vendor image contents not inspected |
| SEC-17 | PASS | secrets as runtime env / occ config from Vault; nothing baked |
| SEC-18/19 | PASS (platform) / GAP (vendor) | build gate #725; vendor images #68 |
| SEC-20 | PASS | Lynis hardening index **86** (gate 80), report of today |
| SEC-21 | PASS (process) | unattended-upgrades + `security_audit` CVE report; `upgrade.disable-web = true`, image + apps pinned, `upgrade_path` for majors |
| SEC-22 | **GAP** | gap 11 |
| SEC-23/24 | **GAP** | auditd inactive in LXC (gap 12) |
| SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban (contract_audit) |
| SEC-30 (app) | PASS | brute-force protection on, `simpleSignUpLink` off, no debug, code integrity ✓, data directory protected ✓, security headers ✓, old SSE disabled |
| SEC-35/36 | PASS | `docs/licensing.md` (AGPL, approved) |

## logging
| ID | Verdict | Evidence |
|---|---|---|
| INF-27 | PASS / **GAP** | promtail active; container stdout in Loki (402 lines/h); application log not shipped (gap 4) |
| INF-28/29 | PASS | labels `host/env/job/container`; retention 90 d |
| INF-30/31 | PASS | JSON application log (`loglevel 2`), no secrets observed |
| INF-32 | **GAP** | no `audit` label for login events (gap 4) |

## monitoring
| ID | Verdict | Evidence |
|---|---|---|
| INF-33/34 | PASS | targets `node`, `cadvisor`, 4 blackbox probes (`/`, `status.php`, signaling, recording) all `up` |
| INF-35 | **GAP** | no application metrics (gap 5) |
| INF-39 | GAP (platform) | no per-service alerts/dashboards (Authentik gap 12) |
| SVC (health) | **GAP** | setupchecks: missing indices (gap 7), Talk HPB mismatch + no Client Push (gap 8); cron mode `cron`, last run 08:10Z ✓ |

## backup
| ID | Verdict | Evidence |
|---|---|---|
| INF-41 | PASS / **GAP** | `docs/backup.md` class A + C; PBS ct 503: 21 snapshots, latest 2026-10-02T01:39Z; PG `pg_dumpall` daily; **files: single copy** (gap 1) |
| INF-42 | **GAP** | no offsite/second copy of `nextcloud-data` (gap 1); cleartext at the provider (gap 2) |
| INF-43 | PASS | PBS encryption + TLS legs (backup chain) |
| INF-44 | NOT VERIFIED | no restore drill documented |

## pins / versioning / git / docs
| ID | Verdict | Evidence |
|---|---|---|
| GIT-01–05 | PASS | image `nextcloud:34.0.4-apache` pinned; 16 apps pinned with sha256 checksums (`nextcloud_apps_pinned`); renovate for the image |
| GIT-13/16 | GAP (platform) | unsigned automation commits |
| SVC-18/19 | GAP (platform) | NetBox empty |
| SVC-23 (contract) | PASS | `scripts/check_service_contract.py` passing; containers via `service_scaffold`; `contract_audit` PASS=11 FAIL=0 |
| SVC-37 | GAP → fixed | service page created |


## Closure — 2026-10-02

| Outcome | Gaps |
|---|---|
| **Fixed, applied ×2 (`changed=0`), verified** | 1 (second copy of the files: #731), 4 (application log in Loki with `audit` + CrowdSec parsing: #730, #732), 5 (application metrics: #729), 6 (Redis DB 3: #728), 7 (DB indices: #728), 13 (service page: #727) |
| **Decision pending (owner merges the proposal)** | 2 (cleartext at the provider → doc-platform-core #69), 3 (vendor root entrypoint → #68 §1 clause + register OH-3 in #724), 10 (break-glass → #65 A) |
| **Platform passes (every service at once)** | 9 IdP group-claim scope, 11 read-only rootfs + tmpfs, 12 auditd in LXC (hypervisor-level audit or Wazuh syscheck — hardening walk) |
| **Next service's walk** | 8 Talk HPB version + Client Push → `collab` |
| **Note** | 14 hostname length (NAM-03, owner) |

Found on the way and fixed in the roles, not only for this service: role-level `vars:` in `playbooks/crowdsec-agents.yml` had been silently overriding every host group's agent collections (now inventory data — #732); the promtail role could not read any log inside a Docker volume (`promtail_acl_traverse` — #732); a CrowdSec collection install never counted as a change, so parsers were loaded only on the next unrelated restart (#732); the promtail role's ACL tasks broke `--check` on a first run (#730).
