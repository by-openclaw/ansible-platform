# role: gitlab_rbac

Group-based GitLab RBAC via the API (CE has no OIDC group-sync): Authentik groups → project/group roles.

Everything runs through one idempotent reconciler (`files/reconcile.rb`, `gitlab-rails runner`, no token) driven by `templates/desired.json.j2`; it prints one line per change and `RBAC_DONE changes=N` (`changes=0` on a clean re-run).

| Section | Vars | What it reconciles |
|---|---|---|
| Instance policy | `gitlab_rbac_settings` | any `ApplicationSetting` key — sign-up off, visibility caps, **diagram rendering** (`kroki_*`, `plantuml_*`, `diagramsnet_*` → `roles/diagrams`, browser-reachable HTTPS names) |
| Admins | `gitlab_rbac_instance_admins` (+`_enforce_admin_exact`) | mirrors Authentik `gitlab-admins`; root exempt |
| Groups | `gitlab_rbac_groups` | `platform/{infra,apps,devops,docs,support}` — visibility + creation levels |
| Memberships | `gitlab_rbac_members` | Owner = `adm_*` only; users Developer (code) / Reporter (docs) / Developer (support) |
| Cleanup | `gitlab_rbac_delete_projects` | throwaway projects from bring-up |
| **Projects** | `gitlab_rbac_projects` | create-if-absent under a group (README initialised); reconciles description, visibility, **`service_desk` flag**. Ships `platform/support/helpdesk` = Service Desk home + runbook/KB repo |
| **Integrations** | `gitlab_rbac_integrations` | per-project **Discord** channel: `{project, type: discord, webhook_vault_path, events, branches}` — the webhook is read from Vault at run time (never in git). Empty list = inert |

Service Desk goes live only once `roles/gitlab` enables mailroom (`gitlab_service_desk_enabled`, see that README); the project flag is safe to set early.

Run: `ansible-playbook -i inventories/prod playbooks/gitlab-rbac.yml`
