# role: dbgate

DbGate Community (web edition, Docker image `dbgate/dbgate`, GPL-3.0) on `lxc-dbgate-01` (SVC `10.1.3.141`). The free edition only: the platform uses no paid plan (owner, 2026-11-05).

One DbGate instance per **view**, declared once in `inventories/prod/group_vars/all/dbgate.yml` (`platform_dbgate_views`):

| View | Name | Host port | Authentik application | Group admitted | Extra sources |
|---|---|---|---|---|---|
| admin | `dbgate.<domain>` | 3000 | `dbgate` | `dbgate-admins` | — |
| cerebrum-01 | `sql-cerebrum-01.<domain>` | 3001 | `dbgate-cerebrum` | `cerebrum-operators` | Cerebrum instance 01's server |
| cerebrum-02 | `sql-cerebrum-02.<domain>` | 3002 | `dbgate-cerebrum` | `cerebrum-operators` | Cerebrum instance 02's server |

## What it does

1. Reads each Authentik application's OIDC client from Vault (`<env>/dbgate/oidc`, `<env>/dbgate/oidc-cerebrum`, minted by `roles/authentik`) and refuses to start a view without one: DbGate without its `OAUTH_*` settings serves every visitor without a sign-in.
2. Through `roles/service_scaffold`: one container per view (`dbgate-<view>`, pinned image, published on the SVC address and the view's port, a named volume for `/root/.dbgate`), one internal-only Traefik route per name (the platform's internal ranges and admin desks, plus the view's own `allow_from`), the SSO registration assertion.
3. Sign-in: DbGate's web OAuth settings — Authentik's authorize/token/end-session endpoints, scope `openid profile email groups`, the login from `preferred_username`, `OAUTH_ALLOWED_GROUPS` = the view's group. DbGate returns to the page it was opened on, so each view's root (`https://<name>/`) is its redirect in Authentik.

4. SQL Server: each view's one connection (the view's `sql`), DbGate's predefined-connection settings (`CONNECTIONS`, `SERVER_`, `USER_`, `PASSWORD_`, `ALLOWED_DATABASES_`, both editions). The login and its password are `roles/cerebrum_db`'s (Vault `<env>/mssql/<host>/<instance>/<login>`); DbGate reads them and refuses a view without one. The connection uses the instance's split-DNS name (`cerebrum-db.<tier zone>`), encrypted (`USE_SSL_`), verifying the zone wildcard the instance presents (public CA, no trust override), through the portable driver (`tedious`).

| View | Login | Rights (inside these databases only) | Databases listed |
|---|---|---|---|
| admin | `dbgate_admin` | `db_owner` | every Cerebrum database + `Federation` |
| cerebrum-01 | `dbgate_cerebrum_01` | `db_datareader`, `db_datawriter` | `Cerebrum_01`, `Federation` |
| cerebrum-02 | `dbgate_cerebrum_02` | `db_datareader`, `db_datawriter` | `Cerebrum_02`, `Federation` |

No login has a server role: the server itself stays Windows authentication. The `Federation` database is granted at the first `roles/cerebrum_db` run after the Federation service has created it.

Order: `playbooks/authentik.yml` (the applications), `playbooks/cerebrum.yml --tags sql` (the logins, the instance's firewall admits the DbGate host), then `ansible-playbook playbooks/dbgate.yml`.

## Controls

| Control | Where |
|---|---|
| NIS2 Art. 21(2)(i), (j); ISO 27001 A.5.15, A.8.5 | sign-in through Authentik only (MFA there), one group per view, a view never starts without its application |
| ISO 27001 A.8.20, A.8.22 | internal-only routes, per-view sources, the DOCKER-USER catalog (`docker_firewall.yml`), the SVC address only |
| ISO 27001 A.8.9 | the image pinned to an exact version; every setting a variable |
| ISO 27001 A.8.15 | container logs to the journal, shipped to Loki (roles/docker) |
