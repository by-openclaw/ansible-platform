# role: vaultwarden (Docker)

Vaultwarden **Bitwarden-compatible password manager** on `lxc-vaultwarden-01`
(SVC `10.1.3.160`). Single `vaultwarden/server` container (pinned).
Upgrade = bump `vaultwarden_image` tag.

> Distinct from Vault (`roles/vault`, `vault.by-research.be`) — Vault is the
> infra secrets backend; Vaultwarden is the end-user password manager.

- depends `base` + `docker`. Includes `postgres_db` to create its own DB+role.
- **Postgres** over `sslmode=verify-full` (`sslrootcert` = mounted host CA
  bundle) — shared cluster Postgres.
- `ADMIN_TOKEN` (48-char random) generated once and stored in the controller
  secret store (`vaultwarden.json`, `no_log`); gates the `/admin` break-glass
  panel. DB password loaded from `db-pgsql-vaultwarden.json`.
- `SIGNUPS_ALLOWED=false` (invite/admin-created accounts only).
- Persistent `vaultwarden-data` volume (`/data`); host CA store mounted.
- **Internal-only:** published via `traefik_route` (`vaultwarden.by-research.be`,
  wildcard TLS + `ipAllowList`). Expose publicly later by adding a Cloudflare
  record + flipping `traefik_route_internal_only`.

SSO is a later phase — built SSO-ready; admin via `ADMIN_TOKEN` is break-glass.
Health: `/alive` on `:80` (first start runs DB migrations — be patient).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/vaultwarden.yml`.
Requires the FW DMZ→SVC `:80` rule + Unbound override (opnsense catalog).
