# role: base

Baseline provisioning for every cluster LXC. `debian-13-standard` ships
`openssh-server` but is otherwise minimal (no `curl`, `dnsutils`, `jq`, …). This
role guarantees a consistent toolbox + sshd/cron running **before** service roles
(traefik, postgresql, redis, …) run.

Apply via `playbooks/base.yml` (targets the `cluster` group) or as a role
dependency. Idempotent.
