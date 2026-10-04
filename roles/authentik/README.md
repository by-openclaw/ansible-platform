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

## RADIUS (administrator logins on network devices)

`tasks/radius.yml`, `templates/radius.yaml.j2`, defaults `authentik_radius_*`. Authentik's own
RADIUS provider, served by the outpost container `authentik-radius` on every instance
(`1812/udp`): a device is given both instances as primary and secondary server.

| What | Where |
|------|-------|
| Who may ask | `authentik_radius_client_networks` — the management network of the switch fabric (`platform_mgmt_zones.fabric`); the same sources in the DOCKER-USER catalog (`mgmt:fabric`) |
| Who is accepted | members of `authentik_radius_group` (`platform_infra_admins_group`), nobody else |
| Login | the user name and `password;code` — the flow asks for the second factor, the code of the authenticator app follows the password after a semicolon |
| Shared secret of the devices | Vault `{env}/authentik/radius`, field `shared_secret` (created once) |
| Outpost token | issued by Authentik, copy in Vault `{env}/authentik/radius-outpost` |
| Protocol | PAP (device administration). Port authentication (802.1X/EAP) is not served by this provider |

Self-test, on every run and for each instance: a client container on the monitoring host sends
one login of the probe account (accepted) and one with a wrong password (refused). The probe is
a service account whose only right is the self-test provider — own shared secret, reachable
from the monitoring host only, a password-only flow that only an outpost can run. The devices'
secret is never used by the test.

Signal: `RadiusOutpostDown` (fewer outposts running than instances).

A device still needs its own side: the two servers, the shared secret from Vault, and the
vendor attribute that maps an accepted login to a privilege level (added as a property mapping
of the provider when the first device is linked).
