# role: portainer

One web console for **both** container worlds: the k3s cluster and every Docker-in-LXC host. The server runs **inside the cluster** (no new guest), each Docker host runs the agent bound to its own SVC address, and humans arrive through the platform reverse proxy with Authentik in front.

## Contract map

| Concern | How |
|---|---|
| Image pins | `portainer_version` drives both `portainer/portainer-ce:<v>-alpine` (server) and `portainer/agent:<v>` (agents). Never a moving tag. |
| Placement | server = Deployment + PVC (`local-path`) in the `portainer` namespace; agents = one compose stack per Docker host. |
| SSO | **native OIDC against Authentik** (`AuthenticationMethod=3`, client credentials from Vault `prod/portainer/oidc`, minted by `roles/authentik`): the console records *who* restarted a container, and the IdP restricts sign-in to `platform-admins`. Applied through the API, drift-gated. |
| Access | route `portainer.<domain>`, internal-only, with Authentik forwardAuth as a second gate in front. The local admin is a break-glass account whose password is declared from Vault (`prod/portainer/admin`), so the first-run wizard can never be claimed by whoever opens the page first. |
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
- First deployment only: `--check` fails on the Vault secrets because a get-or-create cannot mint under check mode. Run the play once for real, after which `--check` is clean.
- Sign-in shows "Login with OAuth"; the local admin form stays available for break-glass.
