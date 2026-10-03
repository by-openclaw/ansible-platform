# PostgreSQL (shared cluster) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: postgresql`). Role `roles/postgresql` (the engine) + `roles/postgres_db` (every consumer's database, owner role, extensions, DBA logins — one owner per concern), play `playbooks/postgresql.yml`, guest `lxc-pgsql-01`. Audit: [`docs/audits/postgresql-2026-10-03.md`](../audits/postgresql-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — no user interface (`sso: none`); every connection is a role with `scram-sha-256` over TLS (`hostssl` from the service CIDRs only), one owner role per service database (`roles/postgres_db`, password in Vault `secret/{env}/<service>/db-pgsql`), the DBA login `pgadmin_dba` (predefined read/monitor roles, CONNECT everywhere) for pgAdmin, `postgres_exporter` for metrics.
2. **Authentik application:** none (pgAdmin carries the human access).
3. **Access model:** superuser `postgres` = break-glass (password in Vault `postgres/superuser`; local socket `trust` inside the container is how the roles administer it); application roles own exactly one database (PUBLIC `CONNECT` revoked on all 11 service databases); `pg_hba`: local trust, loopback scram, `hostssl` scram from the service networks (v4 + v6), the exporter from the Docker gateway.
4. **Vault paths:** `secret/{env}/postgres/superuser`, `secret/{env}/<service>/db-pgsql` (per consumer), `secret/{env}/pgadmin/dba`.
5. **Ansible adapter + vars:** `roles/postgresql` (`defaults/main.yml`: pin `pg_image`, listener, TLS = the platform wildcard, server flags (connections, logging, ciphers), backup; `templates/pg_hba.conf.j2`; `tasks/container.yml` the server flags, `backup.yml` the daily dump, `tls.yml` the certificate); `roles/postgresql_exporter` sidecar.
6. **Removal notes:** not removable — 11 services' databases. Rebuild = play + restore the latest `pg_dumpall` (`/var/lib/postgresql/backups`, 7 days, in the PBS image).

## Notifications (services/0005)

1. **Transport:** none — the server sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus `postgres_exporter` (`:9187`) + `node` + `cadvisor` → the platform's PostgreSQL alerts → Alertmanager → Discord/mail.
4. **Logs:** the server log (connections, disconnections, DDL, checkpoints) → journald → promtail → Loki; the exporter on journald.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class A (`docs/backup.md`): `pg-backup.timer` 02:00 → `pg_dumpall | gzip` → `/var/lib/postgresql/backups/all-<date>.sql.gz` (7 days, tmpfiles) inside the PBS guest image (encrypted, replicated to the off-site S3); the `pgdata` volume in the same image. Restore = play + `psql -f` of the dump (or the PBS image).
