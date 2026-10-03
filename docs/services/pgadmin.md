# pgAdmin — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: pgadmin`). Role `roles/pgadmin`, play `playbooks/pgadmin.yml`, guest `lxc-pgadmin-01` (ct 540). Audit: [`docs/audits/pgadmin-2026-10-02.md`](../audits/pgadmin-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — pgAdmin's OAuth2 source against Authentik (`AUTHENTICATION_SOURCES: oauth2, internal`), auto-created users, access limited by the `groups` claim to the pgAdmin admin group; MFA at Authentik.
2. **Authentik application:** OIDC, slug `pgadmin` (`group_vars/all/sso.yml`).
3. **Access model:** people sign in through Authentik; every user gets the shared cluster server (per-user entry with `PasswordExecCommand`, no password stored in pgAdmin); the connection runs as the dedicated DBA login `pgadmin_dba` (read everything, monitor, maintain, signal — never superuser). Break-glass: pgAdmin's local `admin` (password in Vault); the cluster superuser stays in Vault for `psql`, audited, rotated after use.
4. **Vault paths:** `secret/{env}/pgadmin/admin` (local admin), `pgadmin/oidc` (`roles/authentik`), `pgadmin/db-pgsql` (pgAdmin's own state database, `postgres_db`), `pgadmin/dba` (the DBA login, minted by the role), `mail/pgadmin` (service mailbox).
5. **Ansible adapter + vars:** `roles/pgadmin` (`defaults/main.yml`: pin, ports, the DBA login and its memberships; `vars/main.yml` = the container environment; the DBA login through `roles/postgres_db` (role-only mode: memberships + CONNECT on every database), `servers.yml` + `servers_import.yml` the shared server and the passexec file, `files/pg_provision.py` the per-user entries; `service_scaffold` for DB, mailbox, route, container).
6. **Removal notes:** `playbooks/decommission-service.yml`; class B — pgAdmin's state database (cluster PostgreSQL) and the `pgadmin-data` volume are archived before destroy; the DBA login on the cluster is dropped with the service (its Vault document stays).

## Notifications (services/0005)

1. **Transport:** SMTP through the `pgadmin@<domain>` mailbox (password resets of local accounts; nothing else).
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus blackbox `https://pgadmin.<domain>/` → Alertmanager → Discord/mail (platform); pgAdmin exposes no Prometheus metrics.
4. **Logs:** the container → journald → promtail → Loki (`container="pgadmin"`, gunicorn access + app log).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B (`docs/backup.md`): pgAdmin's state (servers, preferences) in its own database on the cluster (daily `pg_dumpall`), `pgadmin-data` (the passexec file, sessions) in PBS (daily, ct 540). Restore = play (the passexec file and the DBA login are recreated from Vault) + database restore.
