# role: postgres_db

Reusable per-app helper: provisions **one** application database + owner role on
the shared cluster PostgreSQL (`lxc-pgsql-01`). Each app's playbook includes it
so the app owns its own DB lifecycle — the `postgresql` engine role does **not**
create app DBs (separation of concerns).

Idempotent via `docker exec` (delegated to the Postgres host; local socket =
trust). The password is generated once and stored in the controller secret store
as `db-pgsql-<name>.json` (consumed by the app, `sslmode=verify-full`).

```yaml
- name: "Create the NetBox database"
  ansible.builtin.include_role:
    name: postgres_db
  vars:
    postgres_db_name: netbox
    postgres_db_user: netbox
```

| var | default | purpose |
|---|---|---|
| `postgres_db_name` | — (required) | database name |
| `postgres_db_user` | — (required) | owner role |
| `postgres_db_host` | `lxc-pgsql-01` | Postgres host (delegate target) |
| `postgres_db_container` | `postgres` | container name |
| `postgres_db_secret_dir` | controller secret store | where the password is written |

> NetBox/Authentik run their own schema migrations into the (empty) database on
> first start — this role only creates the empty DB + role.
