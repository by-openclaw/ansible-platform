# role: authentik (Docker)

Authentik **SSO / Identity Provider** on `lxc-authentik-01` (SVC `10.1.3.130`).
`server` + `worker` containers (same pinned `ghcr.io/goauthentik/server` image).
Upgrade = bump `authentik_image` tag.

- depends `base` + `docker`. Includes `postgres_db` to create its own DB+role.
- **Postgres** over `sslmode=verify-full` (`SSLROOTCERT` = mounted host CA bundle);
  **Redis** over TLS (`TLS_REQS=required`, password) — both shared cluster svc.
- Secrets (`AUTHENTIK_SECRET_KEY`, bootstrap admin password + token) generated
  once and stored in the controller secret store (`authentik.json`, `no_log`).
  DB/Redis passwords loaded from their own secret files.
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
