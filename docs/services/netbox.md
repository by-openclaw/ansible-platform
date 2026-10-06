# NetBox — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: netbox`). Role `roles/netbox`, play `playbooks/netbox.yml`, guest `lxc-nbox-01` (ct 520). Audit: [`docs/audits/netbox-2026-10-02.md`](../audits/netbox-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — social-auth OpenID Connect against Authentik (`REMOTE_AUTH_BACKEND`), `groups` claim; the pipeline step in `extra.py` makes members of the admin group superusers at login.
2. **Authentik application:** OIDC, slug `netbox` (`group_vars/all/sso.yml`), bound to `netbox-admins` (NetBox is an administration tool: only admins sign in).
3. **Access model:** superusers = the active members of `netbox-admins` (people.yml) + the local `admin`, reconciled on every play run (`tasks/rbac.yml`: the flag is read and set in NetBox's database on the PostgreSQL leader, because NetBox's REST API does not expose it); no self-registration. Break-glass: the local `admin` account — password and a validated API token in Vault (through NetBox's REST API: a token is provisioned by the role when the held one no longer authenticates; Vault holds the whole credential `nbt_<key>.<secret>`).
4. **Vault paths:** `secret/{env}/netbox/admin` (secret key, superuser password + API token), `netbox/db-pgsql` (`postgres_db`), `netbox/oidc` (`roles/authentik`), `mail/netbox` (service mailbox), shared `redis/admin`.
5. **Ansible adapter + vars:** `roles/netbox` (`defaults/main.yml`: pin, DB/Redis, OIDC group, metrics; `vars/main.yml` = the whole container environment; `templates/extra.py.j2` = the OIDC role pipeline; `service_scaffold` for DB + extensions, mailbox, route and the three containers).
6. **Removal notes:** `playbooks/decommission-service.yml`; class B — the PostgreSQL database (the CMDB) and the `netbox-media` volume are archived before destroy.

## Notifications (services/0005)

1. **Transport:** SMTP to the mail host, STARTTLS, as the service mailbox `netbox@<domain>` (password resets, event notifications).
2. **What is sent:** NetBox user notifications; nothing to operators by mail (webhooks none).
3. **Alerting path:** Prometheus — blackbox `https://netbox.<domain>/` plus the `netbox` job (`:8080/metrics`, django-prometheus: request latency, DB and cache counters) → Alertmanager → Discord/mail (platform rules).
4. **Logs:** the three containers (app, worker, housekeeping) → journald → promtail → Loki (`container="netbox"` …); NetBox's own change log and journal live in the database.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B (`docs/backup.md`): the database in the shared PostgreSQL cluster (daily `pg_dumpall`), the `netbox-media` volume and the configuration in PBS (daily, ct 520). Restore = play + database restore.
