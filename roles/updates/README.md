# Role: `updates`

OS patching and unattended-upgrades for every LXC/VM in the fleet.

## Why this exists

The two VMs (`vm-adguard-01`, `vm-mailcow-01`) were built with
`unattended-upgrades`; **none of the cluster LXCs were**, and no playbook or role
in this repo applied OS patches. The result, measured 2026-08-17: every Debian 13
LXC sat **89–100 packages behind, 31–37 of them security** (openssl, openssh,
systemd, libc6, python3.13), while the two VMs were fully current.

This role fixes both halves: it applies the backlog, and it installs the
mechanism so the drift does not come back.

## What it does

| Stage | File | Effect |
|---|---|---|
| preflight | `tasks/preflight.yml` | Refresh index, print the pending-package list (the diff), record running services + containers |
| apt | `tasks/apt.yml` | `apt upgrade` (non-interactive, `confold`), autoremove/autoclean, `needrestart -r a` |
| unattended | `tasks/unattended.yml` | Install + configure `unattended-upgrades`, security origins only, enable timers |
| verify | `tasks/verify.yml` | Re-read services/containers, **fail the play** if anything that was running is now down |

`preflight` and `verify` are tagged `always`, so a `--check` run still gives you
the full pending-package list per host without changing anything.

## Safety model

- **`updates_apply` defaults to `false`.** Importing the role, or running it via
  `site.yml`, never patches. The apply pass only runs with `-e updates_apply=true`.
- **`needrestart` cannot restart the container runtime.**
  `templates/99-ansible-blacklist.conf.j2` blocks `docker.service` and
  `containerd.service`, because restarting Docker bounces every container on the
  host. Those units are reported, never auto-restarted.
- **`unattended-upgrades` is security-origin only** and blacklists
  `docker-ce`/`containerd.io`. Point releases stay gated behind a deliberate run
  of this playbook.
- **Reboots are opt-in** (`updates_reboot: false`). LXCs take their kernel from
  the PVE host, so a "reboot" is a container restart — the operator picks the
  window.
- **Verification fails the play**, and the playbook sets `any_errors_fatal`, so a
  bad package stops the rollout at one host instead of the whole fleet.

## ⚠️ Vault re-seals on container restart

`lxc-vault-01` runs Vault in Docker. If that container restarts, Vault comes back
**sealed** and every consumer fails until it is unsealed with 3 of the 5 keys in
`~/.openclaw/workspace/infra/secrets/vault-init.json`. That is why docker is
blacklisted from `needrestart` and why `vault` is in the last patch wave. After
patching wave 4, confirm `sealed:false` before calling the run done.

## Patch waves

Defined as inventory groups in `inventories/prod/hosts.yml`, ordered by blast
radius:

| Wave | Group | Hosts | Rationale |
|---|---|---|---|
| 0 | `patch_canary` | pgadmin | Nothing depends on it — safe to break first |
| 2 | `patch_wave2` | vaultwarden, nextcloud, netbox, crowdsec | Leaf services, no internal dependents |
| 3 | `patch_wave3` | redis, netbird, traefik, adguard | Dependents exist but recover on restart |
| 4 | `patch_wave4` | postgresql, authentik, vault, mailcow | Everything above depends on these |

## Usage

```bash
# Dry run — shows the pending package list for every host, changes nothing
ansible-playbook -i inventories/prod/hosts.yml playbooks/updates.yml

# Canary first
ansible-playbook -i inventories/prod/hosts.yml playbooks/updates.yml \
  -e updates_apply=true --limit patch_canary

# Then wave by wave
ansible-playbook -i inventories/prod/hosts.yml playbooks/updates.yml \
  -e updates_apply=true --limit patch_wave2

# Mechanism only, no backlog (installs unattended-upgrades everywhere)
ansible-playbook -i inventories/prod/hosts.yml playbooks/updates.yml \
  --tags unattended
```

## Variables

See `defaults/main.yml`. The ones worth knowing:

| Variable | Default | Purpose |
|---|---|---|
| `updates_apply` | `false` | Gate on the apply pass — must be set explicitly |
| `updates_upgrade_type` | `safe` | `safe` = `apt upgrade`; `full` = `dist-upgrade` |
| `updates_needrestart` | `true` | Restart services linked against upgraded libs |
| `updates_needrestart_blacklist_services` | docker, containerd | Never auto-restarted |
| `updates_reboot` | `false` | Reboot when the host asks for one |
| `updates_unattended_enabled` | `true` | Install the recurring mechanism |
| `updates_unattended_auto_reboot` | `false` | Let unattended-upgrades reboot |
