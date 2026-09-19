# role: portainer

The container console, on its **own guest** `lxc-portainer-01` (SVC, 2 vCPU / 2 GiB / 10 GiB). One web UI for every Docker host (agent per host, inventory group `docker_hosts`) and for the k3s cluster (agent inside the cluster — the console itself does not run in the cluster). Born through `service_scaffold` like every service.

## Contract map

| Concern | How |
|---|---|
| Guest | `infra-terraform-proxmox environments/prod/svc-portainer.tf` (vmid 511, 10.1.3.196 / fd01:3::196). Inventory group `portainer`, member of `cluster` (node exporter, logs, patching) and `docker_hosts` (per-container metrics). |
| Image pins | `portainer_version` drives `portainer/portainer-ce:<v>-alpine` and `portainer/agent:<v>`. Never a moving tag (guarded in CI). |
| SSO | **native OIDC** against Authentik (`authentik_oidc_apps` slug `portainer`, `restrict_to_group` platform-admins, client in Vault `prod/portainer/oidc`), applied through the API and drift-gated. The local admin (`prod/portainer/admin`) is break-glass only and declared from Vault, so the first-run wizard can never be claimed. |
| Route | `portainer.<domain>`, internal-only, via the scaffold (no forwardAuth: the console authenticates people itself). |
| Firewall | catalog aliases `host4/host6_portainer`, `port_portainer`; rule `PASS DMZ Traefik→SVC portainer` (v4/v6). Agents: SVC→SVC and SVC→DMZ are open by default policy; each agent's ufw accepts the console host only. |
| Mailbox | `portainer@<domain>` via the scaffold + `playbooks/mailboxes.yml` fan-out. |
| Audit | `contract_audit` row `SVC-PORTAINER` (API answers on the console host). |
| Agents | Docker: compose stack on each `docker_hosts` member, shared key read **once** from Vault `prod/portainer/agent`. Kubernetes: Deployment + NodePort 30778 in namespace `portainer-agent`. Environments registered through the API from the inventory, idempotent. |
| Monitoring | node exporter + promtail (group `cluster`), cAdvisor (group `docker_hosts`), HTTPS probe on the route (read from the live Traefik host list). |
| Backup | class D: no platform data; the guest is in the PBS jobs and the play rebuilds the console from Vault + inventory. |
| Lifecycle | `-e portainer_state=absent` stops and removes the stack; the guest is removed by Terraform; Vault paths stay (archive rule). |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/portainer.yml
```

## Runbook

- Sign-in: "Login with OAuth" → Authentik. Only `platform-admins` get through the IdP.
- An environment shows down: `docker ps` in `/opt/portainer-agent` on that host (Docker) or `kubectl -n portainer-agent get pods` (cluster); the console host must reach port 9001 / 30778.
- First deployment only: `--check` fails on the Vault secrets (a get-or-create cannot mint under check mode). Run once for real; afterwards `--check` is clean.
- Rotating the agent key: `vault_secret_force_fields` on `prod/portainer/agent`, then re-run — server and every agent are rendered from the same value.
