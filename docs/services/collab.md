# Collab backends — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: collab`). Roles `roles/onlyoffice` + `roles/nextcloud_collab`, play `playbooks/collab.yml` (containers on `lxc-collab-01`, then the occ bindings on the Nextcloud host). Audit: [`docs/audits/collab-2026-10-02.md`](../audits/collab-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — **no human login surface**: nobody signs in to `office.<domain>`, the signaling, recording or whiteboard endpoints. The person is authenticated by Nextcloud (Authentik OIDC); these backends trust Nextcloud server-to-server.
2. **Authentik application:** none (catalog `sso: none`). Browser traffic to the backends carries tokens Nextcloud issued (ONLYOFFICE JWT, Talk HPB session tickets, whiteboard JWT); the public routes carry the platform's rate limit and CrowdSec bouncer.
3. **Access model:** whoever may use Nextcloud (`nextcloud-users`) may use Talk/Docs/Whiteboard through it; Talk rooms, document shares and boards follow Nextcloud's own sharing.
4. **Vault paths:** `secret/{env}/collab/backend` (signaling, internal, TURN and recording secrets — get-or-create), `secret/{env}/onlyoffice/jwt` (connector JWT), both read on the collab host and on the Nextcloud host for the occ bindings.
5. **Ansible adapter + vars:** `roles/nextcloud_collab` (compose stack, Traefik path routes on the Nextcloud FQDN, ufw), `roles/onlyoffice` (compose stack, route on `office.<domain>`), `roles/nextcloud/tasks/collab.yml` (occ: signaling/TURN/STUN/recording servers, whiteboard URL + secret, ONLYOFFICE connector).
6. **Removal notes:** `playbooks/decommission-service.yml`; the Nextcloud side keeps working without the backends (no HPB = peer-to-peer calls only, no Docs editing).

## Notifications (services/0005)

1. **Transport:** none of its own (no mailbox); users are notified by Nextcloud (Talk mentions, shares).
2. **What is sent:** nothing from these backends.
3. **Alerting path:** Prometheus blackbox (`office.<domain>/healthcheck`, `/standalone-signaling/api/v1/welcome`, `/recording/api/v1/welcome`, TCP `3478`) → Alertmanager → Discord/mail (platform).
4. **Logs:** every container → journald → promtail → Loki (`container=~"collab-.*|onlyoffice-.*"`).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B — stateless backends (document cache, recording temp, whiteboard room state); the guest is in PBS daily; secrets come back from Vault on the next play run.
