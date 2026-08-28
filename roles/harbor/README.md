# Role: harbor — and the complete service chain (TEMPLATE)

Harbor (OCI container registry + Trivy scanning) on `lxc-harbor-01` (SVC 10.1.3.240).
Docker-compose stack: image **blobs → SeaweedFS S3**, **metadata → cluster Postgres**,
its **own bundled Redis**, **Authentik OIDC**, TLS terminated at **Traefik**. Also a
**pull-through proxy cache** so it replaces Docker Hub (rate-limit-proof, scannable).

> **This role is the reference TEMPLATE for a complete service.** Every box below is
> part of the chain — miss one and the service is half-wired. Rows marked *automatic*
> are inherited (nothing to write); *explicit* rows are the per-service edits. This
> same list is the manifest a generic `deploy-service.yml` / `decommission-service.yml`
> iterates (platform topic 6).

## The complete chain

| # | Component | Harbor value | Where you declare it | Kind |
|---|-----------|--------------|----------------------|------|
| 1 | **Guest** (VM/LXC) | `lxc-harbor-01`, VMID 590, .240, 4c/8G/30G | `infra-terraform-proxmox` → `environments/prod/svc-harbor.tf` | explicit |
| 2 | **Inventory** | `harbor` group under `cluster` | `inventories/prod/hosts.yml` | explicit |
| 3 | **Authentik OIDC app + group** | `harbor` app, `harbor-admins` | `roles/authentik/defaults/main.yml` | explicit |
| 4 | **Postgres DB + role** | `harbor` DB (via `postgres_db`) | included by `roles/harbor/tasks/main.yml` | via role |
| 5 | **SeaweedFS S3 bucket** | `harbor-registry` (via `seaweedfs_bucket`) | included by `roles/harbor/tasks/main.yml` | via role |
| 6 | **Secrets** | `fabric/harbor.json` (+ db/s3/oidc) → mirror to Vault | `tasks/secrets.yml` + `playbooks/secrets-to-vault.yml` | via role |
| 7 | **Ansible role** | install → OIDC → proxy-cache | `roles/harbor` | explicit |
| 8 | **Traefik route** | `harbor.by-research.be` (internal-only) | included by `roles/harbor/tasks/main.yml` | via role |
| 9 | **Split-DNS** | `lxc-harbor-01`.240 + `harbor`→Traefik | `inventories/prod/group_vars/opnsense.yml` | explicit |
| 10 | **OPNsense firewall** | `port_harbor` + DMZ Traefik→SVC rule | `inventories/prod/group_vars/opnsense.yml` | explicit |
| 11 | **Hardening** | sshd 22222 / no-root / fail2ban | `playbooks/hardening.yml -l lxc-harbor-01` | automatic (in inventory) |
| 12 | **CrowdSec agent** | log processor → central LAPI | `playbooks/crowdsec-agents.yml` | automatic (in `cluster`) |
| 13 | **JumpServer asset** | DevOps node, session-recorded | `roles/jumpserver/defaults/main.yml` (#170) | explicit |
| 14 | **Backup** | vzdump → NFS + PBS/S3 | node all-guests jobs | automatic (all-guests) |
| 15 | **NetBox (CMDB)** | register the host (services/0003) | NetBox — sync not yet built | follow-up |
| 16 | **Monitoring** | node-exporter (host) + Harbor `/metrics` | `node-exporter.yml` (auto) + dashboards-as-code | partial (exporter auto; app-metrics follow-up) |
| 17 | **VPN reach** | internal route + NetBird routes `10.1.0.0/16` | — | automatic |
| 18 | **Decommission** | catalog entry (reverse of all above) | `roles/service_decommission/defaults/main.yml` | explicit |

## Deploy order (each step idempotent)

1. `playbooks/authentik.yml` — creates the `harbor` OIDC app + `harbor-admins`, writes `fabric/app-oidc-harbor.json`.
2. Terraform `apply` `svc-harbor.tf` → guest boots; host already in inventory.
3. `playbooks/hardening.yml -l lxc-harbor-01`.
4. `playbooks/opnsense-unbound-overrides.yml` + the OPNsense catalog apply (split-DNS + Traefik→SVC rule).
5. `playbooks/harbor.yml` — DB → S3 bucket → secrets → install → OIDC → proxy-cache → Traefik route.
6. `playbooks/secrets-to-vault.yml` — mirror Harbor's new fabric secrets into Vault.
7. `playbooks/jumpserver.yml --tags reconcile` — register the bastion asset (after #170).
8. **GitLab tie-in** — create a Harbor robot account + set GitLab CI vars so pipelines push scanned/signed images.

## Using it as Docker Hub

Configure a project's / node's container runtime to mirror `docker.io` at Harbor, or
pull explicitly: `docker pull harbor.by-research.be/dockerhub/library/nginx:latest`.
The first pull caches; later pulls are local. Serves Docker today, Swarm/k3s + Helm
(OCI) tomorrow — all identical OCI pulls.

## Decommission (reverse chain)

`ansible-playbook … playbooks/decommission-service.yml -e decommission_target=harbor`
once a `harbor` entry (db, secrets, traefik_route, authentik_app, crowdsec_machine,
guest, split_dns) is added to the `service_decommission` catalog — then `terraform
destroy` the guest.
