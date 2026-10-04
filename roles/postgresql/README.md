# role: postgresql (Docker)

One member of the shared **PostgreSQL 17 cluster** (services/0004): three members under
**Patroni**, the leader elected through etcd (`roles/etcd`, colocated), the other two
streaming from it. Internal-only — a TCP service, **not** behind Traefik. Consumers connect to
the data endpoint (`roles/dbproxy`), which follows the leader.

Run: `ansible-playbook playbooks/postgresql.yml` (members one at a time, the first member first).

## What the role does

- **Image**: builds `platform/postgres-patroni:<server version>-p<rev>` on the member FROM the
  pinned `pg_image`, adding Patroni (`pg_patroni_version`, exact apt pin from the image's own
  PGDG repository). Same base, same glibc collations, same binaries as the standalone server.
  Upgrade = bump `pg_image` / `pg_patroni_version` (then `pg_platform_rev`).
- **Container** (through `roles/service_scaffold`): Patroni is the container's process and
  starts PostgreSQL; runs as the `postgres` uid, **read-only root filesystem**, no capability;
  data on the `pgdata` volume. Published on the member's service address + loopback: `5432`
  (PostgreSQL) and `8008` (Patroni REST API).
- **Three situations, one role** (`tasks/container.yml`):
  - nothing runs → a new member: it copies the leader's data (`pg_basebackup`) and streams;
  - the standalone server runs → the conversion: a fresh logical dump (the nightly job's unit,
    run now), then Patroni **adopts the data directory unchanged** and leads;
  - a member runs → converge; a leader hands the leadership over before its container is
    replaced by an image change.
- **Configuration**: `patroni.yml` (member identity, etcd, credentials — `0400`, re-read on
  SIGHUP), `pg_hba.conf` (ours, via `hba_file`: scram over TLS from the service networks,
  replication between the members), and the **dynamic configuration** `dcs.yml` (what must be
  identical on every member: connections, locks, WAL, logging, failover timing) converged in
  etcd with `patronictl edit-config --replace`. A parameter that needs a restart is flagged
  *pending restart* and applied explicitly: `-e pg_apply_pending_restart=true`.
- **Failover**: `pg_patroni_ttl` (30 s) bounds how long a dead leader keeps the cluster without
  one. `pg_synchronous_mode: true` — a commit waits for one replica, so a failover loses no
  acknowledged transaction; with no replica available the leader keeps accepting writes.
- **TLS**: the shared wildcard certificate (`roles/tls_cert`), server TLS 1.2+, replication with
  `sslmode=verify-full`; the REST API is HTTPS, its write operations need a password.
- **Secrets** (Vault, get-or-create): `postgres/superuser`, `postgres/replication`,
  `postgres/patroni-api`; the etcd credential is read from `etcd/root` (owner: `roles/etcd`).
- **Logins and databases** are not created here: every service's play uses `roles/postgres_db`,
  which runs on the cluster's leader. The role itself only asks that role for the replication
  login.
- **Backup**: `pg-backup.timer` on every member, dumping only where the leader runs
  (`pg_dumpall | gzip`, kept `pg_backup_keep_days`).
- **Verification** (`tasks/verify.yml`, end of the play): every member present, one leader,
  every other member streaming on the leader's timeline.

## Operating it

| Need | How |
|---|---|
| Who leads, who streams | `docker exec postgres patronictl -c /etc/postgres/patroni/patroni.yml list` on any member |
| Planned leader change | `… patronictl … switchover` (the play does it itself before an image change) |
| Re-copy a member that fell behind | `… patronictl … reinit <scope> <member>` |
| Remove ONE member and its data | `-l <member> -e pg_state=absent -e pg_absent_confirm=<member>`, then the play again to rebuild it from the leader |
| Apply a pending restart | `-e pg_apply_pending_restart=true` |

Never promote or demote by hand (`pg_ctl promote`, `REPLICAOF`-style changes): Patroni owns the
roles of the members.

## Limits

- `pg_max_connections` (400) and `pg_log_connections` (on): the 100-connection image default
  was exhausted twice on 2026-09-22 and took every service behind Authentik down. They live in
  the dynamic configuration now (`templates/dcs.yml.j2`).
- The three members share one hypervisor and one storage pool: the cluster covers the loss or
  the maintenance of a guest, a container or a PostgreSQL process — not the loss of the host.
- The endpoint guest is single: it is stateless and restarts in seconds, but while it is down
  consumers cannot reach the leader.
