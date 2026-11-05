# DbGate — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: dbgate`). Role `roles/dbgate`, play `playbooks/dbgate.yml`, guest `lxc-dbgate-01` (ct 541, `infra-terraform-proxmox` `environments/prod/svc-dbgate.tf`). DbGate Community, the free edition only (GPL-3.0): the platform uses no paid plan (owner, 2026-11-05).

The views (`inventories/prod/group_vars/all/dbgate.yml`, `platform_dbgate_views`), one DbGate instance each:

| View | Name | What it shows (phase 2) | Group |
|---|---|---|---|
| admin | `dbgate.<domain>` | every platform database | `dbgate-admins` |
| cerebrum-01 | `sql-cerebrum-01.<domain>` | `Cerebrum_01` + the Federation database | `cerebrum-operators` |
| cerebrum-02 | `sql-cerebrum-02.<domain>` | `Cerebrum_02` + the Federation database | `cerebrum-operators` |

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — DbGate's web OAuth settings against Authentik (`OAUTH_*`), the login from `preferred_username`, access limited by the `groups` claim (`OAUTH_ALLOWED_GROUPS` = the view's group); MFA at Authentik. A view never starts without its application (DbGate without `OAUTH_*` serves anyone).
2. **Authentik applications:** OIDC, slugs `dbgate` (the administrators' view) and `dbgate-cerebrum` (the Cerebrum views; one redirect per view root) — `group_vars/all/sso.yml`.
3. **Access model:** people sign in through Authentik with their own account; what a view shows is decided by its connections (declared by the role) and by the database login each connection uses (rights on those databases only). DbGate's own users and roles are a paid feature and are not used.
4. **Vault paths:** `secret/{env}/dbgate/oidc`, `dbgate/oidc-cerebrum` (`roles/authentik`); phase 2: the per-view database logins.
5. **Ansible adapter + vars:** `roles/dbgate` (`defaults/main.yml`: pin, ports, OAuth settings; `vars/main.yml`: the containers and routes built from the views; `service_scaffold` for containers and routes).
6. **Removal notes:** `playbooks/decommission-service.yml`; the `dbgate-<view>-data` volumes (saved queries, preferences) are kept.

## Notifications (services/0005)

1. **Transport:** none (no mailbox: DbGate sends no mail).
2. **What is sent:** nothing.
3. **Alerting path:** Prometheus blackbox on each route → Alertmanager → Discord/mail (platform); DbGate exposes no Prometheus metrics.
4. **Logs:** the containers → journald → promtail → Loki (`container="dbgate-<view>"`). At each sign-in DbGate logs the identity claims it received (login, groups) — identity data, no secret.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B: no database of its own; the guest (with the per-view volumes) in PBS (daily, ct 541). Restore = play (containers, routes and sign-in are declared) + the volumes from the guest backup.
