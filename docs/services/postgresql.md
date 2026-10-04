# PostgreSQL (shared cluster) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: postgresql`). Role `roles/postgresql` (the engine) + `roles/postgres_db` (every consumer's database, owner role, extensions, DBA logins — one owner per concern), play `playbooks/postgresql.yml`, guests `lxc-pgsql-01`, `lxc-pgsql-02`, `lxc-pgsql-03` — three members under Patroni, the leader elected through etcd (`roles/etcd`, on the same guests); consumers connect to the data endpoint ([dbproxy](dbproxy.md)). Audit: [`docs/audits/postgresql-2026-10-03.md`](../audits/postgresql-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — no user interface (`sso: none`); every connection is a role with `scram-sha-256` over TLS (`hostssl` from the service CIDRs only), one owner role per service database (`roles/postgres_db`, password in Vault `secret/{env}/<service>/db-pgsql`), the DBA login `pgadmin_dba` (predefined read/monitor roles, CONNECT everywhere) for pgAdmin, `postgres_exporter` for metrics.
2. **Authentik application:** none (pgAdmin carries the human access).
3. **Access model:** superuser `postgres` = break-glass (password in Vault `postgres/superuser`; local socket `trust` inside the container is how the roles administer it); application roles own exactly one database (PUBLIC `CONNECT` revoked on all 11 service databases); `pg_hba`: local trust, loopback scram, `hostssl` scram from the service networks (v4 + v6), streaming replication between the members (login `replicator`, TLS `verify-full`), the exporter from the Docker gateway. Patroni's REST API (`:8008`, HTTPS): read-only health endpoints for the members and the endpoint guest, write operations behind a password; etcd: TLS + the `root` password.
4. **Vault paths:** `secret/{env}/postgres/superuser`, `secret/{env}/postgres/replication`, `secret/{env}/postgres/patroni-api`, `secret/{env}/etcd/root`, `secret/{env}/<service>/db-pgsql` (per consumer), `secret/{env}/pgadmin/dba`.
5. **Ansible adapter + vars:** `roles/postgresql` (`defaults/main.yml`: pins `pg_image` + `pg_patroni_version`, listener, TLS = the platform wildcard, failover timing, backup; `templates/patroni.yml.j2` the member, `dcs.yml.j2` the cluster-wide parameters (connections, logging, WAL), `pg_hba.conf.j2`; `tasks/image.yml` the platform image, `container.yml` the member (adoption, join, leader hand-over), `cluster.yml` the replication login and the dynamic configuration, `verify.yml` the final state, `backup.yml` the daily dump, `absent.yml` one member's teardown); `roles/etcd` the consensus store; `roles/postgres_exporter` on every member.
6. **Removal notes:** not removable — 11 services' databases. One member: `-e pg_state=absent -e pg_absent_confirm=<member>`, then the play rebuilds it from the leader. Whole cluster lost = play (a new cluster is initialised with checksums) + restore the latest `pg_dumpall` (`/var/lib/postgresql/backups` on the member that led, 7 days, in the PBS image).

## Notifications (services/0005)

1. **Transport:** none — the server sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus `postgres_exporter` (`:9187`, every member) + `node` + `cadvisor` → the platform's PostgreSQL alerts (`PostgresLeaderCount`, `PostgresReplicaMissing`, `PostgresDown`, connections) → Alertmanager → Discord/mail.
4. **Logs:** the server log (connections, disconnections, DDL, checkpoints) → journald → promtail → Loki; the exporter on journald.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class A (`docs/backup.md`): `pg-backup.timer` 02:00 on every member, dumping only where the leader runs → `pg_dumpall | gzip` → `/var/lib/postgresql/backups/all-<date>.sql.gz` (7 days, tmpfiles) inside the PBS guest image (encrypted, replicated to the off-site S3); the `pgdata` volume in the same image. Restore = play + `psql -f` of the dump (or the PBS image).

## A member after a guest restart (2026-10-04)

Found while the members took their memory change: Patroni exits cleanly when the guest shuts down, before the Docker daemon stops, so Docker recorded the container as stopped and `unless-stopped` left it down at the next boot — the guest was back, its member was not. Every container of the platform now runs with the restart policy `always` (`roles/service_scaffold`). To start an existing container by hand: `docker start <name>` — never the container module with a bare `state=started`, which recreates it from defaults.

## Planned change of the leader (drills of 2026-10-04)

`playbooks/ha-drill.yml --tags postgresql`: health assertion (every member running or streaming, no replay lag), `patronictl switchover` to the synchronous standby, a write through the endpoint, the former leader following again. First production drill: `lxc-pgsql-01 → lxc-pgsql-02`, the endpoint marked the new leader up at 12:32:32.1 and the former one down at 12:32:33.0; every consumer reconnected by itself (138 of 138 targets, 45 of 45 probes, no alert). Run again at 16:11 for the members' memory change (`lxc-pgsql-02 → lxc-pgsql-01`). The members are equivalent: no switch back.

## Connection budget (2026-10-04)

`pg_max_connections: 400`, 4 GiB per member. Measured on the leader with every consumer connected through the endpoint: Authentik about 60 persistent connections per instance (two instances), GitLab about 40, the others under 10 each — 189 backends when the ceiling was 200 (`PostgresConnectionsCritical`), which is what raised it. Applied without an outage: the setting first (members flagged *pending restart*), then each member's restart for its memory — standbys, a planned switchover, the former leader. A new consumer or a third Authentik instance is a budget question first: `select datname, count(*) from pg_stat_activity group by datname`.
