# role: gitlab (the Omnibus image, a container)

GitLab CE `gitlab_version` as a container of the official Omnibus image (`gitlab/gitlab-ce`, host network; `/etc/gitlab`, `/var/opt/gitlab` with the git-data ZFS mount, `/var/log/gitlab` mounted; the image's own accounts — `update-permissions` re-owns the data once when they differ) on `lxc-gitlab-01`. Every Omnibus command goes through `gitlab_exec` + `gitlab_container` (`group_vars/all/gitlab.yml`); scripts for `gitlab-rails runner` are staged in `gitlab_scripts_dir`, mounted read-only. SSO via Authentik OIDC, cluster Postgres (`sslmode=verify-full`), shared Redis (TLS), S3 (SeaweedFS) for artifacts/uploads/backups, Traefik edge, own mailbox `gitlab@` (Service Desk-ready via `gitlab+<key>@`).

- Vault: `prod/gitlab/{db-pgsql,oidc,smtp,secrets,runner-token}`; GitLab's own secrets written post-install (`gitlab_secrets_vault_path`).
- RBAC = `gitlab_rbac` role (group-based); demo project = `gitlab_demo`; CI templates in `files/ci-templates/` (pre-commit, security-scan).
- Runner = `vm-gitlab-runner-01` (docker executor, **unprivileged**, Kaniko builds) → Harbor.
- Upgrade = `playbooks/gitlab-upgrade.yml` (one rung per minor: the image tag; the container's startup reconfigure runs the migrations). A config change in a running container = `gitlab-ctl reconfigure` in place (no restart).
- **Service Desk / reply-by-email** — **live** (mailroom over IMAPS on `gitlab@`, plus-addressing `gitlab+<key>@`, creds Vault `prod/mail/gitlab`; `gitlab_service_desk_enabled: true`). Dependency is DNS, not a firewall rule: `mail.<domain>` must resolve internally to mailcow (split-DNS record in the FW catalog; SVC→DMZ is allowed by default). Desk project = `platform/support/helpdesk` (`gitlab_rbac`); its address is `Project#service_desk_address` (`gitlab+platform-support-helpdesk-<id>-issue-@`).
- Diagrams (Kroki / PlantUML / drawio) + Discord per-project channels = `gitlab_rbac` (ApplicationSetting + integrations).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/gitlab.yml`

## Backup & restore

Class **B + C**: `gitlab-backup create` in the container (host_job timer `gitlab-backup`, nightly) → S3; the `archive/restore` role is the proven end-to-end path; `/etc/gitlab/gitlab-secrets.json` mirrored in Vault. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `docker exec gitlab gitlab-ctl status` (every service `run:`), `docker exec gitlab gitlab-rake gitlab:check SANITIZE=true`; edge `/users/sign_in` 200 (readiness is IP-allowlisted → 404 from outside is expected).
- Restart: `docker restart gitlab` (runs a reconfigure at start); after config edits rerun the play (reconfigure in place).
- Service Desk check: `docker exec gitlab gitlab-rake gitlab:incoming_email:check` must print `Checking Incoming Email ... Finished`; `docker exec gitlab gitlab-ctl status mailroom` running; mail the helpdesk address → confidential issue by `support-bot` (proven 2026-09-04). If disabled again: set the flag `false`, run the play. Legacy note — `gitlab-rake gitlab:incoming_email:check` must print `Checking IMAP ... Finished` and `Project#service_desk_address` resolves; mail a `gitlab+<project-key>@` address → confidential issue in `platform/support/helpdesk`.
- Common: SSO redirect loop → check the Authentik provider `redirect_uris`; DB auth failure after rotation → rerun the play (re-renders `gitlab.rb`).
