# role: postgresql

Shared **PostgreSQL 17** on `lxc-pgsql-01` (SVC `10.1.3.110`). Internal-only —
a TCP service, **not** behind Traefik. Consumed by Authentik + NetBox over the
SVC network.

- Installs `postgresql-17` + `python3-psycopg2`.
- Listens on loopback + the SVC addresses; `scram-sha-256`; `pg_hba` allows the
  SVC zone only (further locked by the FW).
- **TLS (`ssl=on`):** the shared wildcard `*.by-research.be` cert is distributed
  by the `tls_cert` role (issued once on `lxc-traefik-01`, **not** re-issued
  here). Remote app access is forced over TLS (`hostssl` in `pg_hba`); clients
  connect with `sslmode=verify-full` against the publicly-trusted LE chain.
- **HA-adoptable:** `wal_level=replica` etc. → a future replica / Patroni can
  attach with no rebuild and no data loss (per the deferred-HA design).
- Creates app roles + DBs (`netbox`, `authentik`); passwords generated once and
  stored in the controller secret store (`db-pgsql-<app>.json`, `no_log`).
- Daily `pg_dumpall` backup + retention (NAS offload = follow-up).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/postgresql.yml`
(reaches the SVC LXC via OPNsense ProxyJump, login `root`).

Follow-ups: app→DB `5432` FW catalog rule (lib-first); TLS (end-to-end via the
shared `tls_cert` role); NAS backup offload.
