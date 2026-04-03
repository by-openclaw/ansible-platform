> **Mandatory — read before any work:**
> 1. `workspace/OPERATING-STANDARD.md` — platform rules, quality gates, compliance
> 2. This file — repo-specific context

# CLAUDE.md — ansible-platform

> **Scope:** `platform` | **Component:** `ansible`
> **GitHub:** `by-openclaw/ansible-platform`
> **Layer:** Layer 1 (hardening) / Layer 3 (identity) / Layer 5 (services) — ADR-0006

AI agent context. Read before touching any file.

---

## What this repo does

Ansible playbooks and roles for BY-SYSTEMS platform.
Config management: OS hardening, service deployment, user provisioning.

**NOT Terraform** — this configures OS-level. Terraform provisions the VM, Ansible configures it.

---

## Key files

| File | Why |
|---|---|
| `ansible.cfg` | Default inventory, key, become settings |
| `inventories/poc/hosts.yml` | All hosts on srv-proxmox-poc-01 node (folder = node, not env) |
| `inventories/poc/group_vars/all.yml` | Global vars |
| `roles/hardening/defaults/main.yml` | All hardening defaults — check before overriding |
| `roles/hardening/templates/sshd_config.j2` | Full sshd_config — port 22222 ONLY |
| `playbooks/hardening.yml` | Main hardening entry point |

---

## SSH port is 22222 — not 22

Every inventory host uses `ansible_port: 22222`. Never add `Port 22` to sshd config.
The template replaces sshd_config entirely — .d/ fragments are insufficient.

---

## Current state

| Component | Status |
|---|---|
| Role: hardening (sshd, fail2ban, ufw, postfix) | ✅ implemented |
| Inventory: poc (= node srv-proxmox-poc-01, not env tier) | ✅ hosts defined — all VMs here are env=prod |
| Role: users | ⏸ planned (Layer 3 — post-Vault) |
| Role: vault-agent | ⏸ planned (Layer 2) |

---

## Constraints

> Commit conventions, agent permissions, and operational guardrails → see [`AGENTS.md`](AGENTS.md).

- Every host/group MUST declare `env:` with the explicit tier per VM (ADR-0012). `env` is per-VM, not per-inventory. No label = non-compliant.
- `inventories/poc/` = hosts on node `srv-proxmox-poc-01`. Folder name is node-based. All current hosts = `env: prod`.
- Never hardcode IPs in tasks — use inventory or vars
- All tasks must be idempotent (safe to run twice)
- `ansible-lint` clean before merge
- Check mode must work: `--check --diff`
- Always validate sshd config with `sshd -t` before restarting

---

## Diagram standard

See ADR-0006 §9. Source → `assets/diagrams/`, render → `assets/exports/`, commit + post to Discord.

---

## Cross-repo References

- Naming convention: see `doc-platform-core/docs/adr/0010-naming-and-identity-convention.md`
- Environment tiers: poc/dev/test/staging/acc/prod — always explicit. See `doc-platform-core/docs/adr/0012-environment-tier-standard.md`

---

## Related

- Platform charter: `doc-platform-core/docs/adr/0006-platform-charter.md`
- Terraform: `by-openclaw/infra-terraform-proxmox` (provisions VMs — Ansible configures them)
- RAID: open issues on `by-openclaw/platform-setup`

## GitHub → Discord Release Webhook
This repo has a GitHub webhook configured for `release` events → Discord `#releases` channel (by-openclaw standard).
No discord-notify.yml workflow. No DISCORD_WEBHOOK secret. Discord-native parsing.
See `workspace/docs/stack.md` for the full standard and command to replicate on new repos.
