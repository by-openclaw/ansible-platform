# Playbooks — index & flows

All 71 playbooks in this repo, grouped by scope. Each runs against `inventories/prod/hosts.yml` unless noted. Every playbook also carries a header comment with its own detailed flow; per-role detail lives in each role's `README.md`.

> Convention: **roles** hold the logic + a role README; **playbooks** compose roles for a run. Idempotent; safe to re-run. Merge gate = CI pre-commit; apply is user-driven.

## Table of contents

- [Bootstrap & OS baseline](#bootstrap--os-baseline)
- [Identity & SSO](#identity--sso)
- [Secrets & Vault](#secrets--vault)
- [Firewall / OPNsense / DNS](#firewall--opnsense--dns)
- [Core services](#core-services)
- [DevOps toolchain](#devops-toolchain)
- [Apps](#apps)
- [Observability & security](#observability--security)
- [Backup & lifecycle](#backup--lifecycle)
- [Other](#other)

## Bootstrap & OS baseline

| Playbook | Flow |
|---|---|
| `docker-logging.yml` | Docker container logs → journald → promtail → Loki (INF-27: every stream). json-file was the default, so container stdout never reached Loki. PHASED, deliberately: this play only s |
| `hardening.yml` | Playbook: hardening Applies the hardening role to target hosts. Usage: # All hosts: ansible-playbook playbooks/hardening.yml # Single host: ansible-playbook playbooks/hardening.yml |
| `identity-baseline.yml` | Identity/SSH baseline — identity/0004 §9 roles in contract order: 1 user-mgmt      accounts/groups/sudo/keys ({org}, svc-rune-{env}, svc-ansible-{env}) |
| `patch-cve-report.yml` | Patch + CVE currency report — the evidence loop for security/0003 §6 (patch cadence, LOCKED) and §4 (scan trail). READ-ONLY: reports, never changes. * per guest: pending apt update |
| `site.yml` | Playbook: site.yml — full platform playbook Imports all other playbooks in order. |
| `ssh-agent.yml` | Load the svc SSH keys into the controller's ssh-agent — naming/0002 §5.1: "Ansible runtime — ssh-agent populated via Vault lookup". Ansible-ONLY, no shell scripts: |
| `updates.yml` | Playbook: updates.yml — OS patching for the whole fleet, in blast-radius order. The cluster LXCs shipped with no patch mechanism at all and drifted ~100 |
| `user-mgmt.yml` | Provision OS accounts/groups/sudo/keys per identity/0004 + naming/0002 §5. Safe while connected as root — only ADDS accounts. Scope: -e target=<host|group>. |

## Identity & SSO

| Playbook | Flow |
|---|---|
| `authentik.yml` | Configure PROD Authentik (lxc-authentik-01, SVC) — Docker SSO/IdP. |
| `breakglass-kit.yml` | Assemble the BREAK-GLASS PRINT KIT — one folder grouping every credential that must exist on PAPER in the safe (DR with zero platform dependencies: works with Authentik down, Vault |
| `identity-provision.yml` | Identity provisioning — reconcile the platform_people list into Authentik (users + group memberships) and send each a confirmation email. Authentik is the source of truth; mailboxe |
| `key-age-report.yml` | SSH key rotation compliance — identity/0004 §2 (365-day rotation, NIS2 Art. 21(2)(j) / ISO A.5.17). Reads the `created` metadata stored beside each key's passphrase in Vault: WARN  |
| `keys-rotate.yml` | SSH key rotation — identity/0004 §2: ED25519 only, passphrase MANDATORY, one key per identity, comment {username}@{domain}, private key + passphrase backed up in Vault (passphrase  |
| `opnsense-identity.yml` | OPNsense identity pass (identity/0004 / FW-4a): local break-glass admin `by-research` in the FW's LOCAL user database — WebUI access when LDAP/Authentik is down (the POSIX break-gl |
| `vault-deploy-identity.yml` | Provision the controller's ansible-deploy identity (policy + AppRole) — the root-token replacement for every deploy. Run once (idempotent thereafter). ansible-playbook -i inventori |

## Secrets & Vault

| Playbook | Flow |
|---|---|
| `secrets-to-vault.yml` | Mirror controller fabric secret files -> Vault KV v2 at the ADR convention secret/{env}/{service}/{key} (security/0001 §KV v2 path convention). The fabric-name -> service/key mappi |
| `secrets-validate.yml` | Validate that the secrets in Vault are the REAL, working credentials — by authenticating against each live service with the value pulled from Vault. Data-driven: each check declare |
| `vault-approle.yml` | One-time bootstrap: a minimal AppRole for the Ansible controller — the first R-29 closure step (no more root token for runtime reads). Scope: READ-ONLY on |
| `vault-approles.yml` | Provision a per-service Vault identity (policy + AppRole) for every service (SEC-04 least-privilege policy scoped to its own prefix, SEC-05 AppRole auth). |
| `wazuh.yml` | Security monitoring: Wazuh manager + indexer + dashboard on `lxc-wazuh-01` (vendor single-node, pinned, Vault secrets, edge TLS, Authentik OpenID), then the agent on every guest (FIM, log collection, inventory), enrolled with a Vault-held password. Decommission with `-e wazuh_state=absent`. |
| `vault-backup.yml` | Vault DR backup: install the daily raft-snapshot timer on the vault host and pull the newest snapshot to the controller store for an immediate off-host copy. |
| `vault-kv-sync.yml` | Mirror controller-side secret files into Vault KV v2 (secret/<island>/<name>), per the "secrets in Vault AND local" rule. Idempotent: reads the current Vault |
| `vault-migrate-cleanup.yml` | One-shot cleanup AFTER secrets-to-vault.yml has populated the ADR-convention tree secret/{env}/{service}/{key}. Verify-then-retire, never lossy: A. Old flat entries secret/fabric/< |
| `vault.yml` | Configure PROD Vault (lxc-vault-01, SVC) — Docker secrets backend. |
| `vaultwarden.yml` | Configure PROD Vaultwarden (lxc-vaultwarden-01, SVC) — Docker password manager. |

## Firewall / OPNsense / DNS

| Playbook | Flow |
|---|---|
| `cloudflare-dns.yml` | Manage public Cloudflare DNS for {{ platform_domain }} (exposure model). Controller-side only — no FW/host connection. Apply:  ansible-playbook playbooks/cloudflare-dns.yml |
| `docker-hosts.yml` | Docker baseline on every Docker host (`docker_hosts`): pinned engine, daemon.json (journald + v6), compose v2, and the host-firewall rule that lets container networks reach the host (hairpin to published ports). |
| `cadvisor.yml` | Per-container metrics on every Docker host (inventory group `docker_hosts`): cAdvisor pinned, SVC-bound, scraped by Prometheus (job `cadvisor`), with container restart / memory alerts. Asserts every member really runs Docker. |
| `crowdsec-agents.yml` | Playbook: crowdsec-agents.yml — a CrowdSec log processor on every guest. Standing rule: every LXC/VM runs an agent. Per the CrowdSec multi-server guide, these hosts are LOG PROCESS |
| `crowdsec-fw-bouncer.yml` | Point the OPNsense firewall bouncer at the central CrowdSec LAPI. Three plays, one connection mode each, so no task-level connection switching: 1. local  — plugin settings + reconf |
| `crowdsec.yml` | Playbook: crowdsec.yml — PROD CrowdSec central LAPI/engine (lxc-crowdsec-01, SVC). Native crowdsec daemon: LAPI listens on the LAN for agents + bouncers, base + |
| `opnsense-bootstrap.yml` | OPNsense Bootstrap Playbook One-shot. Run once after fresh OPNsense install. Sets hostname + WAN static IP via OPNsense REST API (uri module). After this, all further config is han |
| `opnsense-build.yml` | One command from a free VMID to a firewall running the whole catalog, in the proven order: VM + seed → firmware/plugins and the Vault-free families with the genesis credential → Unbound overrides → token into Vault → full catalog → CrowdSec → export → uplink proof. Rebuild = `-e opnsense_provision_recreate=true` (+ confirm_prod). |
| `opnsense-config-backup.yml` | OPNsense config export → NFS (issue #13). Runs on the PVE host (has the Synology share mounted at /mnt/pve/poc-backup and reaches the FW over OOB). ansible-playbook -i inventories/ |
| `opnsense-pppoe-rotate.yml` | ISP PPPoE credential: rotate, normalise, or (re)apply — Vault-first (hidden prompt, new KV version + metadata), firewall over SSH + wheel sudo (`<ppps>` edit, `configctl` re-dial), API waits for the gateway, fallback file refreshed from Vault. No sudo on the appliance → stops; the seed applies at the re-seed. Role `opnsense_pppoe`, catalog `opn_wan_pppoe`. |
| `opnsense-unbound-overrides.yml` | Apply opn_unbound.host_overrides (split-DNS: service name -> Traefik / mailcow) to the FW's Unbound through the collection module (lib-opnsense UbHostOverrideManager underneath — l |
| `opnsense.yml` | OPNsense Configuration Playbook Idempotent. Safe to run repeatedly. Configures: system, interfaces (VLANs), DNS, DHCP, NTP, firewall aliases+rules, WireGuard. |

## Core services

| Playbook | Flow |
|---|---|
| `adguard-prod.yml` | Playbook: adguard-prod — configure PROD AdGuard Home (vm-adguard-01) Applies the `adguard` role: install + wildcard TLS + per-VLAN clients + renew. Reach the SVC VLAN via the prod  |
| `mailboxes.yml` | Per-service rx/tx mailboxes (SVC-16) + the mandatory catchall@ (SVC-09), via the reusable mailbox concern-role. Idempotent. NOT here: postmaster@/abuse@ (RFC boxes, mailcow role) a |
| `mailcow.yml` | Playbook: mailcow.yml — PROD mailcow mail server (vm-mailcow-01, DMZ vlan1020) Self-contained mailcow-dockerized stack; vmail on Synology NFS; web UI via |
| `portainer.yml` | One web console for both container worlds: Portainer server in the k3s cluster + an agent on every Docker host, environments registered from the inventory through the API, published internally behind Authentik. |
| `postgresql.yml` | Configure PROD PostgreSQL (lxc-pgsql-01, SVC). |
| `redis.yml` | Configure PROD Redis (lxc-redis-01, SVC). |
| `seaweedfs.yml` | SeaweedFS — S3 object-storage backend (replaces EOL MinIO). Play 1 (PVE host): persistent ZFS dataset tank/data/seaweedfs + bind-mount into lxc-seaweedfs-01 at /data — DATA survive |
| `traefik.yml` | Configure PROD Traefik ingress (lxc-traefik-01, DMZ). |

## DevOps toolchain

| Playbook | Flow |
|---|---|
| `diagrams.yml` | Shared diagram services — Kroki (+ Mermaid) + drawio on lxc-diagrams-01. Internal-only (VPN + FW; no public). Kroki is a server-to-server render API so |
| `gitlab-demo.yml` | GitLab demo project — Kaniko build → registry + GitLab Pages, on the runner. Requires the platform group tree (playbooks/gitlab-rbac.yml) to exist first. |
| `gitlab-project-archive.yml` | GitLab — archive (export) + restore (import) ONE project, via the REST API. Proves per-project backup/restore end-to-end. Uses a short-lived admin token |
| `gitlab-rbac.yml` | GitLab RBAC — reconcile instance admins + groups + memberships from desired state (roles/gitlab_rbac/defaults). Re-run whenever the desired state changes; |
| `gitlab-runner.yml` | GitLab CI runner (Linux + Docker + Kaniko) on vm-gitlab-runner-01. Installs Docker + gitlab-runner, mints/reads the auth token from Vault, and registers via a declarative config.to |
| `gitlab-upgrade.yml` | Sequential upgrade for GitLab CE (#384): latest patch of the current minor first (security releases), then the next minor; each rung re-runs the gitlab role, waits for the migrations and verifies runit + readiness before the next. Dry run by default; apply with `-e upgrade_path_apply=true`. |
| `gitlab.yml` | GitLab CE (#8) — full dependency-composed deploy. Order matters (deps first): Play 1  PVE host    : persistent ZFS git-data bind-mount (survives destroy) |
| `harbor-gitlab-ci.yml` | Harbor <-> GitLab integration (topic 2a): publish the Harbor CI robot creds as GitLab INSTANCE-level CI/CD variables so every pipeline can docker login "$HARBOR_HOST" -u "$HARBOR_R |
| `harbor-upgrade.yml` | Sequential upgrade for Harbor (#384): latest patch of the current minor, then one minor at a time; each rung stops the stack, swaps the install tree, re-prepares and verifies the API health before the next. Dry run by default. |
| `harbor.yml` | Configure PROD Harbor (lxc-harbor-01, SVC 10.1.3.240) — OCI container registry. Order (see roles/harbor/tasks/main.yml): DB -> S3 bucket -> secrets -> install -> |
| `jumpserver.yml` | JumpServer CE bastion/PAM on lxc-jumpserver-01. Self-contained (bundled Postgres + Redis), NON-privileged, Vault-native secrets. Browser SSH/RDP to infra; VPN-only via Traefik. Jum |
| `verdaccio-gitlab-ci.yml` | npm registry for CI (issue: Verdaccio finish → runner must use it). Seeds GitLab INSTANCE-level CI/CD variables so every pipeline (via the shared npm.gitlab-ci.yml template) resolv |
| `verdaccio.yml` | Verdaccio — npm registry + upstream proxy (lxc-verdaccio-01, VPN-only). Guest = infra-terraform-proxmox svc-verdaccio.tf (VMID 505). Born through roles/service_scaffold (mailbox, V |

## Apps

| Playbook | Flow |
|---|---|
| `netbird.yml` | Configure PROD NetBird CE (lxc-netbird-01, SVC) — official MULTI-CONTAINER model: dashboard + management + signal + relay + coturn, behind our Traefik, with |
| `netbox.yml` | Configure PROD NetBox (lxc-nbox-01, SVC) — Docker IPAM/source-of-truth. |
| `nextcloud-upgrade.yml` | Playbook: nextcloud-upgrade.yml — sequential major upgrade for Nextcloud. Nextcloud refuses to skip majors, and each major applies its own database migrations via `occ upgrade`. Ju |
| `k3s.yml` | k3s application platform (vm-k3s-01): pinned k3s server, Harbor registry mirror, per-namespace CI deployers (kubeconfig → Vault + GitLab CI variable), app routes on the platform Traefik (TLS + SSO). |
| `collab.yml` | Nextcloud collaboration backend (#396 phase 2): ONLYOFFICE Docs + Talk HPB/TURN + recording + whiteboard on lxc-collab-01, then the Nextcloud side (apps + occ: signaling, TURN/STUN, recording, whiteboard, ONLYOFFICE connector). |
| `nextcloud.yml` | Configure PROD Nextcloud (lxc-nextcloud-01, SVC) — Docker files/drawio, Contabo S3 primary storage. |
| `pgadmin.yml` | Configure PROD pgAdmin (lxc-pgadmin-01, SVC) — Docker + Traefik route. |
| `step-ca.yml` | step-ca — internal certificate authority (lxc-stepca-01, VPN-only). Guest = infra-terraform-proxmox svc-stepca.tf (VMID 506). Born through roles/service_scaffold. CA key password + |
| `warden.yml` | Configure PROD warden (boot-time orchestrator). Run identity-baseline first. |

## Observability & security

| Playbook | Flow |
|---|---|
| `contract-audit.yml` | Playbook: contract-audit.yml — score every host against the ADR contract (docs/audits/adr-compliance-checklist.md) via the read-only, idempotent contract_audit role. Changes nothin |
| `monitoring.yml` | Monitoring stack on lxc-monitoring-01 (SVC 10.1.3.230): - Prometheus (metrics TSDB + scraper; small local TSDB, 15d) - Loki       (logs; chunks + index in SeaweedFS S3) |
| `node-exporter.yml` | node-exporter on every Linux host (fleet-wide) — Prometheus scrapes each :9100. |
| `promtail.yml` | Playbook: promtail.yml — journald + auditd shipping from every guest to the central Loki (lxc-monitoring-01:3100) — INCLUDING the monitoring host itself |
| `security-audit.yml` | security-audit — fleet CVE / update-currency audit (READ-ONLY; never patches). Flow: 1. Per Linux host (all guests except the FW/nodes): roles/security_audit |

## Backup & lifecycle

| Playbook | Flow |
|---|---|
| `decommission-service.yml` | Force a retired service ABSENT — clean, data-driven decommission. ansible-playbook -i inventories/prod/hosts.yml playbooks/decommission-service.yml \ -e decommission_target=defguar |
| `pbs-pve-storage.yml` | Wire PBS into Proxmox VE: add it as a `pbs` storage + a SECOND backup job. The existing vzdump -> NFS (Synology, storage `poc-backup`) job is left ENABLED |
| `pve-host.yml` | The Proxmox VE hypervisor as code (`roles/pve_host`): apt sources, datacenter options, local admin + OIDC realm from Vault + ACLs, Proxmox firewall with roll-back guard, UI route. Exporters/agents via their own plays (node in the targets). |
| `pbs.yml` | Proxmox Backup Server 4 — vm-pbs-01 (SVC 10.1.3.222) SECOND, independent backup copy (SeaweedFS S3 datastore) alongside the existing PVE vzdump -> NFS (Synology) job, which stays e |

## Other

| Playbook | Flow |
|---|---|
| `certs-sync.yml` | certs-sync — refresh the shared wildcard cert on every TLS consumer. lego renews the wildcard on the Traefik host (cron); Traefik hot-reloads it. Backends (Postgres, Redis, …) hold |
| `db-password-rotate.yml` | Rotate ONE service's PostgreSQL password (SVC-28 >=32 chars; SEC-09 rotation machinery). Order: mint 40-char -> ALTER ROLE -> Vault + fabric working copy. |
