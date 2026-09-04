# role: gitlab (omnibus)

GitLab CE **19.3.0-ce.0** (omnibus, native) on `lxc-gitlab-01`. SSO via Authentik OIDC, cluster Postgres (`sslmode=verify-full`), shared Redis (TLS), S3 (SeaweedFS) for artifacts/uploads/backups, Traefik edge, own mailbox `gitlab@` (Service Desk-ready via `gitlab+<key>@`).

- Vault: `prod/gitlab/{db-pgsql,oidc,smtp,secrets,runner-token}`; GitLab's own secrets written post-install (`gitlab_secrets_vault_path`).
- RBAC = `gitlab_rbac` role (group-based); demo project = `gitlab_demo`; CI templates in `files/ci-templates/` (pre-commit, security-scan).
- Runner = `vm-gitlab-runner-01` (docker executor, **unprivileged**, Kaniko builds) → Harbor.
- Upgrade = bump `gitlab_version` (apt pin); `gitlab-ctl reconfigure` runs via the play.
- **Service Desk / reply-by-email** — **live** (mailroom over IMAPS on `gitlab@`, plus-addressing `gitlab+<key>@`, creds Vault `prod/mail/gitlab`; `gitlab_service_desk_enabled: true`). Dependency is DNS, not a firewall rule: `mail.<domain>` must resolve internally to mailcow (split-DNS record in the FW catalog; SVC→DMZ is allowed by default). Desk project = `platform/support/helpdesk` (`gitlab_rbac`); its address is `Project#service_desk_address` (`gitlab+platform-support-helpdesk-<id>-issue-@`).
- Diagrams (Kroki / PlantUML / drawio) + Discord per-project channels = `gitlab_rbac` (ApplicationSetting + integrations).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/gitlab.yml`

## Backup & restore

Class **B + C**: `gitlab-backup create` (cron `gitlab-backup-to-s3`) → S3; the `archive/restore` role is the proven end-to-end path; `/etc/gitlab/gitlab-secrets.json` mirrored in Vault. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `gitlab-ctl status` (9 services `run:`), `gitlab-rake gitlab:check SANITIZE=true`; edge `/users/sign_in` 200 (readiness is IP-allowlisted → 404 from outside is expected).
- Restart: `gitlab-ctl restart`; after config edits `gitlab-ctl reconfigure`.
- Service Desk check: `gitlab-rake gitlab:incoming_email:check` must print `Checking Incoming Email ... Finished`; `gitlab-ctl status mailroom` running; mail the helpdesk address → confidential issue by `support-bot` (proven 2026-09-04). If disabled again: set the flag `false`, run the play. Legacy note — `gitlab-rake gitlab:incoming_email:check` must print `Checking IMAP ... Finished` and `Project#service_desk_address` resolves; mail a `gitlab+<project-key>@` address → confidential issue in `platform/support/helpdesk`.
- Common: SSO redirect loop → check the Authentik provider `redirect_uris`; DB auth failure after rotation → rerun the play (re-renders `gitlab.rb`).
