# role: authentik (Docker)

Authentik **SSO / Identity Provider** on `lxc-authentik-01` (SVC `10.1.3.130`).
`server` + `worker` containers (same pinned `ghcr.io/goauthentik/server` image).
Upgrade = bump `authentik_image` tag.

- depends `base` + `docker`. Includes `postgres_db` to create its own DB+role.
- **Postgres** over `sslmode=verify-full` (`SSLROOTCERT` = mounted host CA bundle), through
  the data endpoint. No Redis: since 2025.10 Authentik keeps cache, sessions and tasks in
  PostgreSQL.
- Secrets (`AUTHENTIK_SECRET_KEY`, bootstrap admin password + token) generated
  once and stored in the controller secret store (`authentik.json`, `no_log`).
  The database password comes from its own Vault document (owner: `postgres_db`).
- Persistent `media` + `templates` volumes; host CA store mounted; the worker
  gets the Docker socket for outpost management.
- **Internal-only:** published via `traefik_route` (`authentik.by-research.be`,
  wildcard TLS + `ipAllowList`). Expose publicly later by adding a Cloudflare
  record + flipping `traefik_route_internal_only`.

Initial admin = `akadmin` / `authentik_bootstrap_email`; password in
`authentik.json`. Health: `/-/health/ready/` on `:9000`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/authentik.yml`.
Requires the FW DMZ→SVC `:9000` rule + Unbound override (opnsense catalog).

- `authentik_pg_conn_max_age` (300 s) / `authentik_pg_conn_health_checks`: persistent DB connections — the upstream default closed one after every request (~2 new TLS connections/s here), which is how the shared PostgreSQL ceiling was reached on 2026-09-22.

## LDAP (tools without OIDC — the firewall's WebGUI login)

| What | Where |
|------|-------|
| Provider, application, bind account, bind flow | one blueprint, `templates/ldap-provider.yaml.j2` (`tasks/ldap_provider.yml`) |
| Bind flow | `authentik_ldap_flow`: identification, password, login — no second-factor stage (LDAP cannot carry one), and it runs for an outpost only (`require_outpost`): it cannot be opened in a browser |
| Certificate | the platform wildcard, assigned through the API and kept in sync (`tasks/ldap_cert.yml`) — never in the blueprint |
| Outpost | container `authentik-ldap` on the first instance, LDAPS 636 only (`tasks/ldap.yml`) |
| Test, every run | `tasks/ldap_bind_test.yml`: LDAPS to `authentik_ldap_fqdn`, certificate verified against that name, bind with the bind account |

Authentik re-applies every blueprint file hourly: whatever a blueprint sets wins over an API
change within the hour. A setting made through the API (the certificate) must therefore not
appear in any blueprint, and no file may sit in the blueprint directory that this role does not render.
