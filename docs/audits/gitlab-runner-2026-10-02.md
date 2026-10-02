<!-- Header: ADR compliance audit record — gitlab-runner, 2026-10-02. Instrument:
     docs/audits/adr-compliance-checklist.md (every row). Evidence gathered live on
     vm-gitlab-runner-01, the GitLab host, Prometheus/Loki and the PVE node; the fixes ship in
     the same PR, applied twice (changed=0). -->

# ADR compliance audit — gitlab-runner (2026-10-02)

Method: roles/contract_audit (PASS=12 FAIL=0 SKIP=21) + manual walk on the live guest, GitLab, Prometheus/Loki and the PVE node.

**Service:** `gitlab-runner` (`roles/gitlab_runner`, `playbooks/gitlab-runner.yml`) on `vm-gitlab-runner-01` (VM, vmid 561) — no UI (`exposure: admin`, `sso: none`), one container (`gitlab/gitlab-runner`, docker executor on the host's engine, `privileged=false`), instance runner `linux-kaniko` registered with a token minted once on the GitLab host and kept in Vault.
**Verdicts:** **PASS** · **GAP** · **N/A** · **NOT VERIFIED**; gaps are **FIX** (this PR) · **PLATFORM** · **PROPOSE** · **OWNER**. Host-level rows identical to the previous audits carry the same verdict.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | INF-33, INF-39 | No application metrics: the runner's Prometheus listener was never enabled (`listen_address` unset; `:9252` answers nothing) although cadvisor and node are scraped. | **FIX** — `listen_address` in `config.toml`, published on the SVC address, DOCKER-USER rule from `monitoring`, catalog `metrics_port: 9252` → job `gitlab-runner` |
| 2 | SEC-21, GIT-05 | Pin `v19.4.0` while `v19.4.1` (2026-09-24) is current; the runner tracks the GitLab minor. | **FIX** — `v19.4.1` |
| 3 | SVC-23 (catalog) | Catalog row said `pin: null` (the role has a pin) and `monitoring: [node]` while cadvisor already runs and is scraped — the row did not describe the service. | **FIX** — `pin: gitlab_runner_image`, `monitoring: [node, cadvisor, metrics]`, register row |
| 4 | IDN-17, SVC-37 | No `docs/services/gitlab-runner.md`. | **FIX** — this PR |
| 5 | SEC-15 | The runner container runs as root with the host's Docker socket (the docker executor needs the engine; root-equivalent by design, like the Portainer agent). | **PROPOSE** — register OH-10 (#724) |
| 6 | note | Job images are pulled every run (`pull_policy: always`) and never removed: 16 images cached, no prune policy on a 40 GB disk. | **FIX** — weekly `docker image prune` of images unused for 7 days (`roles/host_job`) |
| 7 | note | No distributed cache (`[runners.cache] Type = ""`) — optional; an S3 cache on SeaweedFS would speed builds. Not an ADR requirement. | note |
| 8 | SVC-47 | Decommission: the host side has its absent path (catalog); the runner record in GitLab is not removed by the role (`Ci::Runner` on the GitLab host). | **PLATFORM** — absent path for cross-service objects (same class as the Authentik app of a service) |
| 9 | SEC-22 / NAM-01 / INF-35 / hardening | Writable rootfs; NetBox empty; no alert rule names the runner; LLMNR (`:5355`) listens on the VM (systemd-resolved default, ufw blocks it). | **PLATFORM** |

## Rows

| Area | ID | Verdict | Evidence |
|---|---|---|---|
| naming | NAM-03–08 | PASS | `vm-gitlab-runner-01` → internal A/AAAA + PTR; no service FQDN (no UI) |
| identity | IDN-01 | N/A | no user interface; runner token (instance type) minted by `gitlab-rails runner`, kept in `secret/{env}/gitlab/runner-token`; who runs jobs = GitLab RBAC |
| identity | IDN-17 | GAP → fixed | gap 4 |
| secrets | SEC-01–05, SEC-17 | PASS | the token: Vault → `config.toml` 0600 root (`no_log`); nothing else | <!-- pragma: allowlist secret — names of Vault PATHS, no value -->
| database | SVC-26–29 | N/A | — |
| ingress | SVC-01–04 | N/A | no listener beyond SSH, node/cadvisor and (now) `/metrics`; the runner polls GitLab outbound (`gitlab.<domain>` resolves to Traefik inside — verified after the public names were removed: `gitlab-runner verify … is alive`) |
| certs | SEC-26 | PASS | outbound TLS to Traefik (Let's Encrypt); the dependency proxy on `registry.<domain>` |
| mailbox | SVC-16 | N/A | sends no mail |
| decommission | SVC-47 | PASS / GAP (platform) | catalog row; `service_scaffold` native retire removed the package install; gap 8 |
| hardening | SEC-15 | **GAP** | gap 5 |
| hardening | SEC-20 | PASS | Lynis hardening index **86** |
| hardening | SEC-21 | **GAP** → fixed | gap 2 |
| hardening | SEC-23 | PASS | auditd active (VM); sshd/PAM → Loki with the `audit` label |
| hardening | SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban active; ufw active (8 rules: SSH from OOB/platform, scrapes, Portainer agent, Docker hairpin) |
| logging | INF-27–31 | PASS | container on journald → promtail → Loki; job traces live in GitLab; job containers transient |
| monitoring | INF-33 | **GAP** → fixed | gap 1 |
| monitoring | INF-34 | PASS | `node`, `cadvisor` up |
| monitoring | INF-35/39 | GAP (platform) | gap 9 |
| backup | INF-41 | PASS | class D (stateless; token in Vault); PBS vm 561: 21 snapshots, latest 2026-10-02T02:48Z |
| pins | GIT-01–05 | GAP → fixed | gaps 2, 3 |
| firewall | SVC-56/57 | PASS | CrowdSec agent (linux, sshd, auditd collections); decisions reach the bouncers |
| jobs | integration | PASS | last two jobs of the demo project succeeded (22–23 s); a pipeline is run again after the apply (closure) |
| contract | SVC-23 | PASS / GAP → fixed | `check_service_contract.py` 32/32; `contract_audit` PASS=12 FAIL=0; gap 3 |
