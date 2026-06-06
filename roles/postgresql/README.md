# role: postgresql (Docker)

Shared **PostgreSQL 17** as a Docker container on `lxc-pgsql-01` (SVC
`10.1.3.110`). Internal-only — a TCP service, **not** behind Traefik. Consumed by
Authentik + NetBox over the SVC network.

All-Docker pivot: **upgrade = bump `pg_image` tag** → ansible pulls + recreates
the container; data persists in the `pgdata` named volume. Maps cleanly to a
future k8s Deployment/PVC.

- Pinned `postgres:17` image; depends on `base` + `docker` (nested LXC).
- Retires any prior **native** install first (`migrate.yml` stops/masks
  `postgresql@17-main`) so the container can bind `:5432`.
- Published only on `10.1.3.110:5432` + `127.0.0.1:5432`.
- **TLS (`ssl=on`):** the shared wildcard `*.by-research.be` cert is distributed
  by the `tls_cert` role (owned by the container's postgres uid 999) and mounted
  read-only. Remote app access forced over TLS (`hostssl` in `pg_hba`); clients
  connect `sslmode=verify-full` against the publicly-trusted LE chain.
- `scram-sha-256`; `pg_hba` allows the SVC zone only (further locked by the FW).
- **HA-adoptable:** `wal_level=replica` etc. (server flags) → a future replica /
  Patroni can attach with no rebuild and no data loss.
- Creates app roles + DBs (`netbox`, `authentik`) idempotently via `docker exec`;
  passwords generated once and stored in the controller secret store
  (`db-pgsql-<app>.json`, superuser `db-pgsql-superuser.json`, `no_log`).
- Daily `pg_dumpall` (via `docker exec`) backup + retention (NAS offload = follow-up).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/postgresql.yml`
(reaches the SVC LXC via OPNsense ProxyJump, login `root`).
