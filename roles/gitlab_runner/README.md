# role: gitlab_runner

GitLab Runner on `vm-gitlab-runner-01` (VM, not LXC — docker executor). Registered with a token from Vault `prod/gitlab/runner-token`; **privileged=false**, builds via Kaniko; default job image pinned.

- `gitlab_runner_version` empty = repo latest at install; pin to lock.
- Container logs ride journald (fleet default); job containers are transient.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/gitlab-runner.yml`

## Backup & restore

Class **D** — stateless; re-register by re-running the play (token in Vault). Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `gitlab-runner verify`; `systemctl is-active gitlab-runner`.
- Common: jobs stuck pending → runner unregistered/stale token → rerun the play.
