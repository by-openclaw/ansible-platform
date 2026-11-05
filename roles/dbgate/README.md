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

**Phase 1:** no database connection is declared yet. Phase 2 adds them per view (`CONNECTIONS` with the logins from Vault): the Cerebrum views see their instance's database and the Federation database only, through a login with rights on those two only; the administrators' view sees every database.

Run `playbooks/authentik.yml` first, then `ansible-playbook playbooks/dbgate.yml`.

## Controls

| Control | Where |
|---|---|
| NIS2 Art. 21(2)(i), (j); ISO 27001 A.5.15, A.8.5 | sign-in through Authentik only (MFA there), one group per view, a view never starts without its application |
| ISO 27001 A.8.20, A.8.22 | internal-only routes, per-view sources, the DOCKER-USER catalog (`docker_firewall.yml`), the SVC address only |
| ISO 27001 A.8.9 | the image pinned to an exact version; every setting a variable |
| ISO 27001 A.8.15 | container logs to the journal, shipped to Loki (roles/docker) |
