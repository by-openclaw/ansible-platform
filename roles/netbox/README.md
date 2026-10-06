# role: netbox (Docker)

NetBox **IPAM / source of truth** on the host of the `netbox` group.
`netbox` (web) + `netbox-worker` + `netbox-housekeeping` containers (same pinned
`netboxcommunity/netbox` image). Upgrade = bump the `netbox_image` tag.

- `playbooks/netbox.yml` composes `base` + `docker` + this role; the platform concerns
  (database through `postgres_db`, mailbox, internal Traefik route, the three containers,
  the SSO registration) are declared to `roles/service_scaffold` in `tasks/main.yml`.
- **PostgreSQL** over `DB_SSLMODE=verify-full` (`PGSSLROOTCERT` = mounted host CA
  bundle); **Redis** over TLS (`REDIS_SSL=true`, password) on two logical databases
  (tasks=0, cache=1) — both shared cluster services.
- **Secrets** in Vault (`netbox_vault_path`: secret key, local superuser password, API
  token), read and created by `tasks/secrets.yml` (`no_log`); the database, Redis and OIDC
  secrets come from their own Vault paths.
- Persistent `media` volume; host CA store mounted into every container.
- **Internal only:** published at `netbox_fqdn` through the Traefik route of the scaffold.
- Health: `/login/` (200) on `netbox_listen_ip`:`netbox_host_port` (`tasks/verify.yml`).

## Access rights (`tasks/rbac.yml`)

Sign-in is OpenID Connect against Authentik; `templates/extra.py.j2` (NetBox configuration)
sets the superuser flag of the user who signs in from the `groups` claim. Two things NetBox
does not keep by itself are reconciled on every run:

- **The break-glass API token** of the local account `netbox_superuser_name`, through NetBox's
  REST API: the credential Vault holds is validated with a request it authenticates; when it
  is not valid a token is provisioned with the local account's password and written to Vault,
  and earlier tokens with the description `netbox_token_description` are removed. A v2 token's
  credential is `nbt_<key>.<secret>`, sent as `Bearer` — that whole string is what Vault holds.
- **The superuser flag**: superuser = the active members of `netbox_oidc_superuser_group`
  (people.yml) + the local account; every other user loses the flag at the next run, not only
  at their next sign-in (an open session and personal API tokens would keep the rights until
  then). NetBox's REST API neither returns nor accepts that flag, so it is read and set with
  SQL in NetBox's database (`netbox_user_table`), on the PostgreSQL leader, the way
  `roles/postgres_db` runs its statements. It is the only column this role writes there; a
  NetBox upgrade that renames the table makes the read fail (the play stops, nothing is written).

Run: `ansible-playbook playbooks/netbox.yml` — access rights only: `--tags secrets,rbac`.
Service documentation: `docs/services/netbox.md`.
