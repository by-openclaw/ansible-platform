# role: nextcloud (Docker)

Nextcloud **files / drawio** on `lxc-nextcloud-01` (SVC `10.1.3.170`).
`nextcloud` (web, Apache) + `nextcloud-cron` (background jobs) containers (same
pinned `nextcloud:33-apache` image). Upgrade = bump `nextcloud_image` tag.

- depends `base` + `docker`. Includes `postgres_db` to create its own DB+role.
- **Primary storage = Contabo S3** (object storage, bucket `nextcloud-data`,
  path-style, region `eu2`) via `OBJECTSTORE_S3_*` env — user data (incl. drawio
  diagrams) lives in S3, not on the LXC disk. Bucket is precreated out-of-band
  (`OBJECTSTORE_S3_AUTOCREATE=false`).
- **Postgres** over `verify-full` and **Redis** over TLS — the official image has
  no env for either, so both are enforced in a mounted additional `config.php`
  snippet (`zz-cluster.config.php`: `dbdriveroptions` PDO SSL + `redis.ssl_context`
  with the system CA bundle; Redis is also the `memcache.locking`/distributed
  backend). The host CA store is mounted into every container.
- Secrets: local break-glass admin (`admin` + generated password) stored once in
  the controller secret store (`nextcloud.json`, `no_log`). DB / Redis / S3
  credentials loaded from their own secret files.
- **Internal-only:** published via `traefik_route` (`nextcloud.by-research.be`,
  wildcard TLS + `ipAllowList`). Traefik (`10.1.2.110`) set as `TRUSTED_PROXIES`.
- Post-install (occ): installs + enables the **drawio** app idempotently; asserts
  the S3 object store and Redis locking are active.

Initial admin = local **break-glass** `admin`; password in `nextcloud.json`. SSO
via Authentik is a later phase — the role is built SSO-ready but does not wire
OIDC now. Health: `/status.php` → `{"installed":true}` on `:80`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/nextcloud.yml --vault-password-file .vault_pass`.
Requires the FW DMZ→SVC `:80` rule + Unbound override (opnsense catalog, Phase 3).
