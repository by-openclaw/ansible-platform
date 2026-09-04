# ansible-platform

> Ansible playbooks for BY-SYSTEMS platform — OS hardening, service configuration, provisioning.

**Repo:** `by-openclaw/ansible-platform` (private)
**Layer:** Layer 1 (hardening) → Layer 3 (identity) → Layer 5 (services) — see [ADR-0006](https://github.com/by-openclaw/doc-platform-core/blob/main/docs/adr/0006-platform-charter.md)

---

## Quick start

```bash
# 1. Install requirements
ansible-galaxy collection install -r requirements.yml

# 2. Dry-run (check mode — no changes)
ansible-playbook playbooks/hardening.yml --check --diff

# 3. Apply hardening to all hosts
ansible-playbook playbooks/hardening.yml

# 4. Apply to single host
ansible-playbook playbooks/hardening.yml -l srv-proxmox-poc-01

# 5. Run specific tag only
ansible-playbook playbooks/hardening.yml --tags ssh
```

---

## Repository structure

```
ansible-platform/
├── ansible.cfg                    # Default config (key, inventory, become)
├── requirements.yml               # Collection dependencies
├── inventories/
│   └── poc/
│       ├── hosts.yml              # PoC inventory
│       └── group_vars/
│           ├── all.yml            # Global defaults
│           └── proxmox_nodes.yml  # Proxmox-specific vars
├── playbooks/
│   ├── hardening.yml              # Main hardening playbook
│   └── site.yml                   # Full platform playbook
└── roles/
    └── hardening/                 # OS hardening role (see below)
```

---

## Role: hardening

Applies to all managed hosts (VMs, LXCs, Proxmox nodes). Idempotent — safe to run repeatedly.

### What it does

| Component | What |
|---|---|
| **sshd** | Full sshd_config replacement — port 22222 only, no port 22, key-only auth |
| **fail2ban** | SSH jail on port 22222, optional Proxmox web jail |
| **ufw** | Default deny-all, allow only defined ports from defined networks |
| **postfix** | Optional satellite relay (disabled by default) |

### SSH port

**Port is 22222, not 22.** The role replaces `/etc/ssh/sshd_config` entirely to ensure port 22 is never opened — `.d/` fragment overrides are insufficient because they add a port without removing the default.

### Break-glass

For emergency access when certificates/keys are unavailable:

- Group `break-glass` on the target host can authenticate with password
- **Only from OOB/MGMT networks** (`10.6.224.0/20`, `10.6.240.0/20`)
- Not accessible from internet — enforced by `Match Address` in sshd_config

```bash
# Add user to break-glass group on target host
sudo usermod -aG break-glass by-systems
```

### Key variables (defaults)

| Variable | Default | Description |
|---|---|---|
| `hardening_ssh_port` | `22222` | SSH port |
| `hardening_ssh_allow_groups` | `[by-systems, rune]` | Groups allowed SSH key login |
| `hardening_ssh_break_glass_group` | `break-glass` | Group allowed password login |
| `hardening_ssh_break_glass_networks` | OOB + MGMT | Networks where break-glass is allowed |
| `hardening_fail2ban_ssh_maxretry` | `5` | Attempts before ban |
| `hardening_fail2ban_ssh_bantime` | `3600` | Ban duration (seconds) |
| `hardening_ufw_allowed_ports` | SSH/22222 from OOB | Firewall open rules |
| `hardening_email_relay_enabled` | `false` | Enable postfix relay |

Override per group or host in `inventories/poc/group_vars/` or `host_vars/`.

### Proxmox-specific

`group_vars/proxmox_nodes.yml` adds:
- ufw rules for Proxmox WebUI (8006) and SPICE (3128) from OOB only
- fail2ban jail for Proxmox API

---

## Inventory

```yaml
# inventories/poc/hosts.yml
proxmox_nodes:
  srv-proxmox-poc-01:    # 10.6.224.105
vms:
  vm-debian-bootstrap-test-01:  # 10.6.225.11
```

Add new hosts here. Group vars apply automatically.

---

## Commit convention

[Conventional Commits](https://www.conventionalcommits.org/) — enforced via commitlint.

```
feat(hardening): add postfix relay task
fix(sshd): ensure port 22 fragment removed before template deploy
docs: update README with break-glass instructions
```

---

## References

- [docs/new-service.md](docs/new-service.md) — golden path: how a new service is born compliant (`service_scaffold`)
- [docs/backup.md](docs/backup.md) — backup class · mechanism · restore per stateful service (INF-41) + drill log
- [ADR-0006 — Platform Charter](https://github.com/by-openclaw/doc-platform-core/blob/main/docs/adr/0006-platform-charter.md)
- [Platform RAID tracker](https://github.com/by-openclaw/platform-setup/issues)
