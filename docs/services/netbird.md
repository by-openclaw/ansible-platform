# NetBird — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: netbird`). Role `roles/netbird`, play `playbooks/netbird.yml`, guest `lxc-netbird-01`. Audit: [`docs/audits/netbird-2026-10-02.md`](../audits/netbird-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — Authentik is the direct OIDC login (no bundled IdP): PKCE for the dashboard, device flow for `netbird up`, client credentials for the IdP-manager sync and for the role's own automation.
2. **Authentik application:** OIDC public client, slug `netbird` (`group_vars/all/sso.yml`), redirects `/auth` + `/silent-auth` on `vpn.<domain>` and `http://localhost:53000` (CLI PKCE); the service account `svc-netbird-<env>` holds an RBAC role with user/group reads only (blueprint `identity-core`).
3. **Access model:** IdP-enforced — only `netbird-users` may authenticate (`restrict_to_group`); members of `netbird-admins` are NetBird `admin` and get the full internal route (`vpn-full`); every other peer gets the web `/32` routes. The account owner is the service account's IdP identity (first login in single-account mode); it holds no API token (`enforce-no-human-pat`). No local admin exists; break-glass = Authentik.
4. **Vault paths:** `secret/{env}/netbird/core`, `oidc`, `authentik-sa`, `db-pgsql`, `db-pgsql-events`, `automation` (service-user token), `router-setup-key`.
5. **Ansible adapter + vars:** `roles/netbird` (`defaults/main.yml` = pins, ports, policy; `service_scaffold` containers; `postgres_db`; `traefik_route`; `host_firewall`; `vault_secret`).
6. **Removal notes:** `playbooks/decommission-service.yml`; class A — the two PostgreSQL databases are archived before destroy; the volumes hold only re-downloadable GeoLite data; the Authentik application, the DNS record and the firewall aliases are catalog entries declared `absent`.

## Notifications (services/0005)

1. **Transport:** none from the product (NetBird sends no mail); operator alerting is the platform path.
2. **What is sent:** nothing to users by mail; the dashboard shows peer and user state.
3. **Alerting path:** Prometheus — blackbox `https://vpn.<domain>/` plus the `netbird` job (management `:9224`, signal `:9225`, relay `:9226` `/metrics`: `active_peers`, `relay_peers`, `management_*`) → Alertmanager → Discord/mail (platform rules).
4. **Logs:** five containers → journald → promtail → Loki (`container="netbird-management"` …); the activity events store (`netbird_events`) keeps the audit trail inside the product.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class A (`docs/backup.md`): `netbird` + `netbird_events` on the shared PostgreSQL cluster (daily `pg_dumpall`), guest image in PBS (daily, ct 504). Restore = play + database restore; the GeoLite volumes are re-downloaded by management.
