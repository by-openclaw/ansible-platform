# Jitsi Meet — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: jitsi`). Role `roles/jitsi`, play `playbooks/jitsi.yml`, guest `lxc-jitsi-01`. Audit: [`docs/audits/jitsi-2026-10-02.md`](../audits/jitsi-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — access through Authentik **forwardAuth** on the Traefik route (proxy application `jitsi`, `group_vars/all/sso.yml`); Jitsi itself runs anonymous XMPP auth behind that gate.
2. **Authentik application:** proxy provider, slug `jitsi`, external host `https://meet.<domain>`; group `jitsi-users` only.
3. **Access model:** members of `jitsi-users` open `meet.<domain>` in a browser; every room is reachable to them (no per-room ACL). Native/mobile Jitsi apps cannot pass forwardAuth — browser use only, by design. Media (JVB) reaches the internet on UDP 10000 through the firewall's DNAT.
4. **Vault paths:** `secret/{env}/jitsi/secrets` (component passwords jicofo/jvb/jigasi/jibri, get-or-create); no human accounts.
5. **Ansible adapter + vars:** `roles/jitsi` (compose stack of `jitsi/web`, `prosody`, `jicofo`, `jvb` on one pinned tag; `.env` rendered from the role; `service_scaffold` for the route, firewall and Vault concerns).
6. **Removal notes:** `playbooks/decommission-service.yml`; stateless (class D) — nothing to archive but the guest.

## Notifications (services/0005)

1. **Transport:** none (`mailbox: false`); Jitsi sends no mail.
2. **What is sent:** nothing.
3. **Alerting path:** Prometheus blackbox `https://meet.<domain>/` → Alertmanager → Discord/mail; JVB metrics (`jitsi_jvb_*`, job `jitsi`) for conference/media health.
4. **Logs:** every container → journald → promtail → Loki (`container=~"jitsi-.*"`).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class D — stateless, no recordings; config + secrets regenerable (`docs/backup.md`); the guest is in PBS daily.
