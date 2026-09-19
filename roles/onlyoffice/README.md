# role: onlyoffice

ONLYOFFICE Docs (Document Server, Community edition, AGPL) — the Word/Excel/PowerPoint editor of the Nextcloud front door (#396 phase 2). Docker-in-LXC on `lxc-collab-01` (SVC), pinned `onlyoffice/documentserver:9.4.0.1`. Stores no user data: it opens and saves Nextcloud files in place. Composed through `service_scaffold` (public Traefik route `office.<domain>`, no mailbox, no forwardAuth — the trust between Nextcloud and Docs is the JWT).

## Contract map

| Concern | How |
|---|---|
| Image pin | `onlyoffice_image` — never `:latest`. 9.x Community: no connection cap, single process. |
| TLS / ingress | Traefik is the single TLS point; Docs binds `<svc ip>:8000` on the host (ufw from the internal supernet + VPN); FW rule `PASS DMZ Traefik→SVC collab` (v4/v6, alias `port_collab_backends`). Browsers load the editor from `office.<domain>` (public route, rate-limited); split-DNS override `office` → Traefik so Nextcloud reaches it internally. |
| SSO | none of its own — editors open from a Nextcloud session; every request carries a JWT signed with `jwt_secret` (header `Authorization`). |
| Secrets | `jwt_secret` get-or-created in Vault `prod/onlyoffice/secrets`; rendered into `/opt/onlyoffice/.env` (root 0600). The Nextcloud side (`roles/nextcloud/tasks/collab.yml`) reads the same path. |
| Storage | ONLYOFFICE keeps only caches/logs in named volumes; the documents live in Nextcloud (S3 primary storage). |
| Compose | Debian standalone `docker-compose` (Compose v2), like `roles/jitsi`. |
| Logging | Docker → journald → promtail → Loki (INF-27). |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/collab.yml
```
Bring-up of a new host first: identity-baseline → hardening → docker (meta-dep) → this role → `roles/nextcloud_collab` → Nextcloud side.

## Backup & restore

Class **D** (code) — stateless. Redeploy the play; the JWT comes back from Vault, so the Nextcloud connector keeps working. The LXC itself is in the PBS guest jobs (class A).

## Runbook

- Health: `curl -s http://<svc ip>:8000/healthcheck` → `true`; Nextcloud Settings → ONLYOFFICE must show "Settings have been successfully updated" after a save.
- Editor shows "Document server is not available" → Traefik route `office`, FW rule 1081/1082, or the split-DNS override for `office`.
- "Download failed" inside the editor → Docs cannot reach `StorageUrl` (Nextcloud through Traefik) — check DNS from the container.
- Bump the version: change `onlyoffice_image` → run the play (pull + recreate). Open documents are re-loaded by the users.
