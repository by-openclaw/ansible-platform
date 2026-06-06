# role: netbox (Docker)

NetBox **IPAM / source-of-truth** on `lxc-nbox-01` (SVC `10.1.3.120`).
`netbox` (web) + `netbox-worker` + `netbox-housekeeping` containers (same pinned
`netboxcommunity/netbox` image). Upgrade = bump `netbox_image` tag.

- depends `base` + `docker`. Includes `postgres_db` to create its own DB+role.
- **Postgres** over `DB_SSLMODE=verify-full` (`PGSSLROOTCERT` = mounted host CA
  bundle); **Redis** over TLS (`REDIS_SSL=true`, password) on two logical DBs
  (tasks=0, cache=1) — both shared cluster svc.
- Secrets (`SECRET_KEY`, local superuser password + API token) generated once and
  stored in the controller secret store (`netbox.json`, `no_log`). DB/Redis
  passwords loaded from their own secret files.
- Persistent `media` volume; host CA store mounted into every container.
- **Internal-only:** published via `traefik_route` (`netbox.by-research.be`,
  wildcard TLS + `ipAllowList`). Expose publicly later by adding a Cloudflare
  record + flipping `traefik_route_internal_only`.

Initial admin = local **break-glass** `admin` / `netbox_superuser_email`; password
in `netbox.json`. SSO via Authentik (OIDC/REMOTE_AUTH) is a later phase — the role
is built SSO-ready but does not wire OIDC now. Health: `/login/` (200) on `:8080`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/netbox.yml --vault-password-file .vault_pass`.
Requires the FW DMZ→SVC `:8080` rule + Unbound override (opnsense catalog, Phase B).
