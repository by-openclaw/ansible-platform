# role: jitsi

Jitsi Meet — self-hosted video conferencing (official `jitsi/docker-jitsi-meet`: `web`, `prosody`, `jicofo`, `jvb`). Docker-in-LXC on `lxc-jitsi-01` (SVC). Composed through `service_scaffold` (mailbox `jitsi@`, Traefik route `meet.<domain>`, Vault, audit).

## Contract map

| Concern | How |
|---|---|
| Image pin | `jitsi_image_tag` — a **Docker Hub** `stable-NNNN` tag (the GitHub release `stable-NNNN-N` images are not always published; verify with the registry API before bumping). Never `:latest`. |
| TLS / ingress | Traefik is the single TLS point (`DISABLE_HTTPS=1`); web binds `0.0.0.0:8000` on the host, ufw allows it from the internal supernet + VPN only; FW rule `PASS DMZ Traefik→SVC Jitsi` (v4/v6) |
| SSO | Authentik **forwardAuth** proxy app `jitsi`, access group `jitsi-users` (`platform_people`). v1 = internal participants + SSO. |
| Secrets | component/auth passwords get-or-created in Vault `prod/jitsi/secrets`, rendered into `/opt/jitsi/.env` (root 0640) at run time |
| Media | JVB UDP `10000`. **WAN DNAT for external participants is deferred** together with guest/JWT auth. |
| Compose | Debian standalone `docker-compose` (Compose v2 binary) — this platform's images ship no compose plugin |
| Logging | promtail (journald + Docker json-file → journald) like every host (INF-27) |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/jitsi.yml
```
Bring-up of a new host first: identity-baseline → hardening → docker (meta-dep) → this role.

## Backup & restore

Class **D** (code) — Jitsi is stateless: no recordings/transcripts are kept, rooms are ephemeral. Everything is regenerated from this role + the Vault secrets; the LXC itself is in the PBS/NFS guest jobs (class A). Restore = redeploy the play (secrets come back from Vault, so existing clients' component passwords stay valid). Matrix: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `docker-compose ps` in `/opt/jitsi`; jicofo log must show `Added new videobridge`, jvb log `Joined MUC: jvbbrewery`; `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/` → 200.
- Traefik 502 → the FW reverse-proxy rule or ufw 8000 from `10.1.0.0/16`.
- Meeting audio/video fails for **external** guests → expected until the JVB WAN DNAT + `JVB_ADVERTISE_IPS` land (deferred item).
- Bump the version: change `jitsi_image_tag` → run the play (pulls + recreates); secrets untouched.
