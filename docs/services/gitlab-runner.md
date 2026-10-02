# GitLab Runner — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: gitlab-runner`). Role `roles/gitlab_runner`, play `playbooks/gitlab-runner.yml`, guest `vm-gitlab-runner-01` (VM, vmid 561 — the docker executor needs a real kernel). Audit: [`docs/audits/gitlab-runner-2026-10-02.md`](../audits/gitlab-runner-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — not applicable: the runner has no user interface; it authenticates to GitLab with an instance runner token.
2. **Authentik application:** none (`sso: none`, `exposure: admin`).
3. **Access model:** the instance runner `linux-kaniko` (tags `linux`, `docker`, `kaniko`, untagged jobs too) is minted once on the GitLab host (`gitlab-rails runner`, `Ci::Runner.create!`) and reused; who may run jobs is decided in GitLab (project membership, `roles/gitlab_rbac`). Host access = the platform SSH baseline (22222, keys, admin groups).
4. **Vault paths:** `secret/{env}/gitlab/runner-token` (the runner authentication token; minted by the role, never re-registered).
5. **Ansible adapter + vars:** `roles/gitlab_runner` (`defaults/main.yml`: pin, executor, concurrency, metrics port, image prune; `templates/config.toml.j2` = the whole configuration; `service_scaffold` containers; `host_job` for the weekly prune).
6. **Removal notes:** `playbooks/decommission-service.yml`; class D — stateless: the container and `/etc/gitlab-runner` go, the token document stays in Vault, the runner record in GitLab is removed with the instance (or by hand in the admin area until the role grows an absent path for it).

## Notifications (services/0005)

1. **Transport:** none — the runner sends no mail; job results reach people through GitLab's own notifications (the `gitlab@<domain>` mailbox).
2. **What is sent:** nothing from this host.
3. **Alerting path:** Prometheus — `node`, `cadvisor` and the runner's own `/metrics` (`:9252`: `gitlab_runner_jobs`, `gitlab_runner_errors_total`, version info) → Alertmanager → Discord/mail (platform rules).
4. **Logs:** the runner container → journald → promtail → Loki (`container="gitlab-runner"`); job traces are stored by GitLab, job containers are transient.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class D (`docs/backup.md`): configuration = this role + the Vault token; the guest image in PBS (daily, vm 561) is a convenience. Restore = re-run the play (the runner re-attaches with the same token and system id).
