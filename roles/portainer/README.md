# role: portainer

One web console for **both** container worlds: the k3s cluster and every Docker-in-LXC host. The server runs **inside the cluster** (no new guest), each Docker host runs the agent bound to its own SVC address, and humans arrive through the platform reverse proxy with Authentik in front.

## Contract map

| Concern | How |
|---|---|
| Image pins | `portainer_version` drives both `portainer/portainer-ce:<v>-alpine` (server) and `portainer/agent:<v>` (agents). Never a moving tag. |
| Placement | server = Deployment + PVC (`local-path`) in the `portainer` namespace; agents = one compose stack per Docker host. |
| Access | route `portainer.<domain>`, internal-only, **Authentik forwardAuth** restricted to `platform-admins`. The local admin is a break-glass account whose password is declared from Vault (`prod/portainer/admin`), so the first-run wizard can never be claimed by whoever opens the page first. Native OIDC inside Portainer is the follow-up. |
| Cluster rights | ServiceAccount `portainer` bound to `cluster-admin` — the console manages the cluster it runs in. |
| Agent trust | one shared key in Vault (`prod/portainer/agent`), rendered into each agent's compose file (0600) and into the server; agents accept connections from the platform supernet only (ufw + firewall catalog). |
| Environments | registered through the API from the inventory (`portainer_agent_groups`), idempotent: a host already present is skipped. |
| Backup | class D: the console holds no platform data. Its PVC is convenience state; re-running the play rebuilds it from Vault + inventory. |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/portainer.yml
```

## Runbook

- Server health: `kubectl -n portainer get pods`; the API answers `GET /api/status` behind the ingress.
- An environment shows "down": check the agent on that host (`docker ps` in `/opt/portainer-agent`) and that port 9001 is reachable from the cluster.
- Rotating the agent key: `vault_secret_force_fields` on `prod/portainer/agent`, then re-run the play (server and agents are rendered from the same value).
- The console can restart containers and exec into them. That is why it is internal-only, behind SSO, and limited to one group.
