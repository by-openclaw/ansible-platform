# role: gitlab (omnibus)

GitLab CE **19.3.0-ce.0** (omnibus, native) on `lxc-gitlab-01`. SSO via Authentik OIDC, cluster Postgres (`sslmode=verify-full`), shared Redis (TLS), S3 (SeaweedFS) for artifacts/uploads/backups, Traefik edge, own mailbox `gitlab@` (Service Desk-ready via `gitlab+<key>@`).

- Vault: `prod/gitlab/{db-pgsql,oidc,smtp,secrets,runner-token}`; GitLab's own secrets written post-install (`gitlab_secrets_vault_path`).
- RBAC = `gitlab_rbac` role (group-based); demo project = `gitlab_demo`; CI templates in `files/ci-templates/` (pre-commit, security-scan).
- Runner = `vm-gitlab-runner-01` (docker executor, **unprivileged**, Kaniko builds) → Harbor.
- Upgrade = bump `gitlab_version` (apt pin); `gitlab-ctl reconfigure` runs via the play.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/gitlab.yml`

## Backup & restore

Class **B + C**: `gitlab-backup create` (cron `gitlab-backup-to-s3`) → S3; the `archive/restore` role is the proven end-to-end path; `/etc/gitlab/gitlab-secrets.json` mirrored in Vault. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `gitlab-ctl status` (9 services `run:`), `gitlab-rake gitlab:check SANITIZE=true`; edge `/users/sign_in` 200 (readiness is IP-allowlisted → 404 from outside is expected).
- Restart: `gitlab-ctl restart`; after config edits `gitlab-ctl reconfigure`.
- Common: SSO redirect loop → check the Authentik provider `redirect_uris`; DB auth failure after rotation → rerun the play (re-renders `gitlab.rb`).
