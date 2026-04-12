# Ansible Platform — Setup Guide

This guide covers installing and configuring Ansible on the **Rune VM** for platform automation.

## Prerequisites

- Rune VM running Ubuntu 24.04
- `by-systems` user in `sudo` group
- SSH key `~/.ssh/id_ed25519_rune` available (automation key)
- Python 3.10+ installed

## 1. Install Ansible

```bash
# Install via pip into a dedicated venv (avoid distro package — too old)
sudo apt update && sudo apt install -y python3-pip python3-venv

python3 -m venv ~/.venv/ansible
source ~/.venv/ansible/bin/activate

pip install --upgrade pip
pip install ansible ansible-lint

# Install required collections
ansible-galaxy collection install -r requirements.yml
```

`requirements.yml` defines all collections including `community.opnsense`.

## 2. SSH Configuration

Add to `~/.ssh/config` on Rune VM:

```
Host opnsense-poc
    HostName 10.1.1.1
    User root
    Port 22
    IdentityFile ~/.ssh/id_ed25519_rune
    StrictHostKeyChecking no
    ServerAliveInterval 30
```

> OPNsense does not have `by-systems` OS user — SSH as `root` for bootstrap, then switch to API-only (`svc-rune`) for all Ansible operations via the OPNsense API (no SSH needed after bootstrap).

## 3. Ansible Configuration

`ansible.cfg` (repo root — already committed):

```ini
[defaults]
inventory           = inventories/poc/hosts.yml
remote_user         = by-systems
private_key_file    = ~/.ssh/id_ed25519_rune
host_key_checking   = False
retry_files_enabled = False
stdout_callback     = yaml
callbacks_enabled   = timer, profile_tasks

[privilege_escalation]
become        = True
become_method = sudo
become_user   = root
```

> For OPNsense targets: `become` is not used — all operations go through the OPNsense REST API via `community.opnsense` modules (token auth, not SSH sudo).

## 4. Sudo Configuration

On Rune VM (`by-systems` user):

```bash
# Verify sudo access
sudo -l

# Should include: (ALL) ALL
# If not: sudo visudo → add:
# by-systems ALL=(ALL) NOPASSWD: ALL
```

For OPNsense: no sudo needed — API token auth only.

## 5. Ansible Vault

Secrets (API tokens, WireGuard keys) are encrypted with ansible-vault.

```bash
# Create vault password file (never commit this)
echo "your-vault-password" > ~/.vault_pass
chmod 600 ~/.vault_pass

# Copy to infra/secrets as well (source of truth)
cp ~/.vault_pass /home/by-systems/.openclaw/workspace/infra/secrets/ansible-vault.key
```

`ansible.cfg` uses vault password file automatically — add to config:

```ini
[defaults]
vault_password_file = ~/.vault_pass
```

**Secret storage path:** `infra/secrets/vault.yml` (ansible-vault encrypted)
**Future:** migrate to HashiVault when deployed (ADR-0024 — `identity-sync` Ansible role pattern)

### Create/edit vault secrets

```bash
# Create
ansible-vault create infra/secrets/vault.yml

# Edit
ansible-vault edit infra/secrets/vault.yml

# View
ansible-vault view infra/secrets/vault.yml
```

## 6. OPNsense API Authentication

The `community.opnsense` collection authenticates via OPNsense API key (not SSH).

Create `svc-rune` API key in OPNsense UI:
- System → Access → Users → `svc-rune` → Edit → API keys → Generate

Store in vault:

```yaml
# infra/secrets/vault.yml (ansible-vault encrypted)
opnsense_api_key: "<key>"
opnsense_api_secret: "<secret>"
opnsense_host: "10.1.1.1"
```

Reference in inventory:

```yaml
# inventories/poc/group_vars/opnsense.yml
opnsense_api_key: "{{ vault_opnsense_api_key }}"
opnsense_api_secret: "{{ vault_opnsense_api_secret }}"
opnsense_host: "{{ vault_opnsense_host }}"
```

## 7. Idempotency — ensure() pattern

Every Ansible task against OPNsense **must be idempotent**. The `community.opnsense` modules follow a consistent pattern:

```yaml
- name: Ensure DHCP server configured on MGMT
  puzzle.opnsense.dhcpv4_reservation:
    interface: "opt1"
    state: present
    # ... params
```

- Use `state: present` / `state: absent` — never raw API calls in playbooks
- No `shell:` or `command:` tasks for OPNsense config — always use the collection module
- Bootstrap exception: 2 initial API calls (hostname + WAN IP) via `uri` module in `bootstrap.yml` — documented, one-shot, idempotent guard via `changed_when`

## 8. Running Playbooks

```bash
source ~/.venv/ansible/bin/activate

# Full OPNsense config
ansible-playbook playbooks/opnsense.yml

# Bootstrap only (first boot — sets hostname + WAN IP)
ansible-playbook playbooks/opnsense-bootstrap.yml

# Dry run
ansible-playbook playbooks/opnsense.yml --check --diff

# Specific tags
ansible-playbook playbooks/opnsense.yml --tags wireguard
```

## 9. Verify

```bash
# Ping inventory
ansible all -m ping

# Check OPNsense API reachable
ansible-playbook playbooks/opnsense.yml --tags check --check
```

## References

- Collection docs: <https://docs.ansible.com/ansible/latest/collections/community/opnsense/>
- `roles/opnsense/README.md` — role contract and variables
- ADR-0015: Network/VLAN architecture
- ADR-0024: Identity provisioning pattern (vault → HashiVault migration path)
