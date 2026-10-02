# GitLab CE — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: gitlab`, aliases `registry`, `pages`). Role `roles/gitlab` (+ `roles/gitlab_rbac` for every admin setting, `roles/gitlab_demo`), plays `playbooks/gitlab.yml`, `gitlab-rbac.yml`, `gitlab-upgrade.yml` (version ladder), `gitlab-project-archive.yml`; guest `lxc-gitlab-01` (ct 560). Audit: [`docs/audits/gitlab-2026-10-02.md`](../audits/gitlab-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — OmniAuth OpenID Connect against Authentik (PKCE, `groups` claim); the sign-in page goes straight to Authentik (`omniauth_auto_sign_in_with_provider`), accounts are auto-created on first login and linked by e-mail.
2. **Authentik application:** OIDC confidential client, slug `gitlab` (`group_vars/all/sso.yml`), redirect `/users/auth/openid_connect/callback`.
3. **Access model:** `required_groups` = `gitlab-users` (only members may sign in), `admin_groups` = `gitlab-admins` (instance admins, reconciled by `roles/gitlab_rbac` from `people.yml`); open signup off, import sources restricted, nothing can be made public. Break-glass: the local `root` account (`?auto_sign_in=false`), its password in Vault with GitLab's own secrets.
4. **Vault paths:** `secret/{env}/gitlab/db-pgsql` (`postgres_db`), `gitlab/s3` (`seaweedfs_bucket`), `gitlab/oidc` (`roles/authentik`), `gitlab/secrets` (GitLab's generated secrets + initial root password — DR-critical, written back by the role), `gitlab/runner-token`, `mail/gitlab` (the service mailbox: SMTP + IMAP), shared `redis/admin`.
5. **Ansible adapter + vars:** `roles/gitlab` (`defaults/main.yml`: pin, ports, metrics, backup; `templates/gitlab.rb.j2` = the whole configuration), `roles/gitlab_rbac` (`gitlab_rbac_settings`, groups, members, projects, CI templates, integrations).
6. **Removal notes:** `playbooks/decommission-service.yml`; class B + C — the PostgreSQL database, the git-data ZFS dataset (`tank/data/gitlab`, PVE bind-mount) and the S3 buckets (artifacts, LFS, uploads, packages, registry, backups, …) are archived before destroy; `gitlab/secrets` stays in Vault.

## Notifications (services/0005)

1. **Transport:** SMTP to the mail host, STARTTLS, as the service mailbox `gitlab@<domain>`; Service Desk reads the same mailbox over IMAPS (`gitlab+<key>@<domain>` sub-addressing).
2. **What is sent:** GitLab's user notifications (merge requests, pipelines, issues, Service Desk replies); nothing to operators by mail.
3. **Alerting path:** Prometheus — blackbox `https://gitlab.<domain>/` plus the `gitlab` job (Puma `:8083`, Sidekiq `:8082`, Workhorse `:9229`, Gitaly `:9236`, gitlab-exporter `:9168`) → Alertmanager → Discord/mail (platform rules).
4. **Logs:** files under `/var/log/gitlab` shipped by promtail — `gitlab_audit` (`audit_json`, `auth_json`) and `gitlab_shell` carry the `audit` label (90 d), `gitlab_rails`, `gitlab_nginx`, `gitlab_services` the default class; the container's own stdout → journald. CrowdSec reads the Rails request log (sign-in brute force).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B + C (`docs/backup.md`): nightly `gitlab-backup create` (host timer `gitlab-backup`, 02:30) → S3 `gitlab-backups` (SeaweedFS, 7 days, replicated off-site by the SeaweedFS → Contabo backup), the PostgreSQL database in the cluster's daily `pg_dumpall`, the guest image in PBS (ct 560; the git-data bind-mount is excluded from the image because the GitLab backup holds the repositories). Restore = play + `gitlab-backup restore` with `gitlab/secrets` from Vault.
