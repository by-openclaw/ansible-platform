# Portainer — Setup Runbook

The container console: one web UI for every Docker host (agent per host) and the k3s cluster (agent in the cluster). Runs on its **own guest**, `lxc-portainer-01` (SVC), and is born through `service_scaffold` like every service. It watches and operates containers; it does not monitor or self-heal them (that is Prometheus/Alertmanager and the engines' restart policies).

## 1. Image decision

Portainer CE, `portainer/portainer-ce:<version>-alpine` (server) and `portainer/agent:<version>` (agents), both driven by `portainer_version` in `roles/portainer/defaults/main.yml`. Pinned; the image-pin guard in CI refuses a moving tag. Business edition was not chosen: its extras (per-namespace RBAC, group sync, audit log) are not needed while access is gated by Authentik group at the IdP.

## 2. Services architecture

| piece | where | how |
|---|---|---|
| server | `lxc-portainer-01`, one container, port 9000 on the SVC address | `community.docker.docker_container` (no compose file, no package install) |
| Docker agent | every member of inventory group `docker_hosts`, port 9001 on the host's SVC address | one container per host, shared key from Vault |
| Kubernetes agent | k3s cluster, namespace `portainer-agent`, NodePort 30778 | manifest rendered by the role |
| route | `portainer.<domain>` on the platform Traefik, internal-only | `service_scaffold` → `traefik_route` |

Data: a Docker volume `portainer-data` holding console state only (environments, users, settings). No platform data.

## 3. Pre-requisites

- Guest provisioned by Terraform (`infra-terraform-proxmox environments/prod/svc-portainer.tf`, vmid 511, 10.1.3.196 / fd01:3::196, Debian 13, nesting).
- Bootstrap: `playbooks/identity-baseline.yml -e target=lxc-portainer-01 -e ansible_user=root -e ansible_port=22 -e ansible_ssh_private_key_file=<terraform-pushed key>`, then `playbooks/hardening.yml -e target=lxc-portainer-01`.
- Authentik running (the OIDC client is minted by `playbooks/authentik.yml`).
- Inventory: host in group `portainer`; `portainer` is a child of `cluster`, of `docker_hosts` and of `patch_wave2`.

## 4. Secrets (Vault KV paths)

| path | fields | who writes |
|---|---|---|
| `prod/portainer/admin` | `username`, `password` | roles/portainer (get-or-create) — break-glass local admin, declared so the first-run wizard can never be claimed |
| `prod/portainer/agent` | `secret` | roles/portainer (get-or-create) — shared agent key, server and every agent |
| `prod/portainer/oidc` | `client_id`, `client_secret` | roles/authentik (blueprint) — consumed by roles/portainer |

Rotation: `vault_secret_force_fields` on the path, then re-run the play (server and agents render from the same value).

## 5. Certificates

None on the service. TLS terminates on the platform Traefik (Let's Encrypt wildcard). Agents present a self-signed certificate to the server; trust is the shared agent key, and the API is told `TLSSkipVerify` + `TLSSkipClientVerify` on registration.

## 6. Configuration source (instead of an environment file)

Everything is in `roles/portainer/defaults/main.yml` (version, ports, namespaces, Vault paths, SSO endpoints, per-host switch `portainer_agent`). Console settings that live in Portainer's own database (authentication method, OAuth endpoints, environments) are applied through its API by the role, drift-gated: read first, write only when different.

## 7. Provisioning (instead of docker compose)

`playbooks/portainer.yml`, four plays in dependency order:

1. **console** on `portainer`: Vault secrets, server container, ufw, scaffold (route, mailbox, Vault inventory, SSO assertion).
2. **Docker agent** on `docker_hosts`: asserts the Docker socket exists, reads the key once for the fleet, runs the agent container, ufw accepts the console host only. A host with `portainer_agent: false` gets no agent and any earlier agent removed.
3. **Kubernetes agent** on `k3s`: retires any console left inside the cluster, applies the agent manifest, opens the NodePort to the console host.
4. **registration + SSO** on `portainer`: native OAuth against Authentik first, then one environment per Docker host with an agent plus the cluster, idempotent.

## 8. Exposure / routing

Internal-only: split-DNS `portainer` → Traefik (Unbound override, both families), firewall rule `PASS DMZ Traefik→SVC Portainer` (v4/v6, `port_portainer` = 9000). No public record. Agents: SVC→SVC and SVC→DMZ are open by default policy; each agent's ufw accepts the console host only.

## 9. Installation steps

```
# 1) guest (Terraform) + bootstrap (identity-baseline, hardening)      — see §3
# 2) SSO client
ansible-playbook -i inventories/prod/hosts.yml playbooks/authentik.yml
# 3) firewall objects — ALWAYS dry-run first, exact scope
ansible-playbook -i inventories/prod/hosts.yml playbooks/opnsense.yml --check \
  -e '{"opn_fw_only": ["host4_portainer","host6_portainer","port_portainer","PASS DMZ Traefik→SVC Portainer (reverse proxy)","PASS DMZ Traefik→SVC Portainer (reverse proxy v6)"]}'
ansible-playbook -i inventories/prod/hosts.yml playbooks/opnsense-unbound-overrides.yml
# 4) the service — twice; the second run must report changed=0
ansible-playbook -i inventories/prod/hosts.yml playbooks/portainer.yml
# 5) the per-guest layer: promtail, crowdsec-agents, cadvisor, node-exporter, jumpserver, monitoring
# 6) proofs
ansible-playbook -i inventories/prod/hosts.yml playbooks/contract-audit.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/secrets-validate.yml
```

First deployment only: `--check` fails on the Vault secrets (a get-or-create cannot mint under check mode); run once for real, after which `--check` is clean.

## 10. Post-install configuration

None by hand. Authentication method, OAuth endpoints and environments are declared in the role and applied through the API.

## 11. Upgrade procedure

Bump `portainer_version` (Renovate opens the pull request), re-run the play: server and agents are recreated on the new pin. Portainer migrates its own database at start. Agents and server must share a major version.

## 12. Health checks

- `GET /api/status` on the console host: `{"Version": "<version>", …}` (contract-audit row `SVC-PORTAINER`).
- `GET /api/settings/public` → `AuthenticationMethod: 3` (OAuth).
- HTTPS probe on the route (Prometheus reads the live Traefik host list); cAdvisor on the guest; node exporter; promtail → Loki.
- `kubectl -n portainer-agent get pods` on the cluster; `docker ps -f name=portainer-agent` on a Docker host.

## 13. Troubleshooting

| symptom | cause | fix |
|---|---|---|
| Gateway Timeout on the route | firewall rule not applied (catalog only) | §9 step 3 |
| local login form, no OAuth button | play 4 did not run or failed before the SSO task | re-run the play; read `ptr_apply` output |
| environment down in the console | agent stopped, or port 9001/30778 closed to the console host | `docker ps` on the host, ufw comment `Portainer` |
| 400 "Invalid certificate file" on registration | missing `TLSSkipClientVerify` | fixed in the role, re-run |

Incident 2026-09-19 (#454): the first role version installed Debian's `docker-compose`, which replaced the Docker engine on the docker-ce mail VM. A service role never installs `docker*`/`containerd*` packages.

## 14. Identity and access

Native OIDC against Authentik (`authentik_oidc_apps` slug `portainer`, `restrict_to_group: platform-admins`). Portainer auto-creates the user on first login with `preferred_username`. The local admin is break-glass only (Vault). The console can restart containers and open shells: internal-only route, IdP-restricted group.

## 15. Notifications

Mailbox `portainer@<domain>` (scaffold, delegates per the platform rule). Portainer CE has no outbound notifications; operational alerts about containers come from Prometheus (`ContainerRestarting`, `ContainerMemoryNearLimit`, `TargetDown`).
