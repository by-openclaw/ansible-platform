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

`requirements.yml` defines all collections, including the two OPNsense ones: `ansibleguy.opnsense` (firewall rules/aliases — ADR-mandated) and `by_systems.opnsense` (our lib-opnsense-backed MVC modules: NAT, syslog, Kea, users/API keys, …).

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

> OPNsense hosts are `connection: local` API targets — no SSH from Ansible. The firewall's identity (users, SSH keys, interfaces, the `oob-admin` break-glass/genesis credential) comes from the **seed** (infra-terraform-proxmox `modules/vm-opnsense/seed`); Ansible talks to the MVC API as `svc-ansible-prod` (naming/0002 §3) with a token it mints itself (§6).

## 3. Ansible Configuration

`ansible.cfg` (repo root — already committed):

```ini
[defaults]
inventory           = inventories/poc/hosts.yml   ; per-env: -i inventories/prod | -i inventories/test
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

> For OPNsense targets: `become` is not used — all operations go through the OPNsense REST/MVC API via the `ansibleguy.opnsense` + `by_systems.opnsense` modules (token auth, not SSH sudo). The inventory sets `ansible_connection: local`, `ansible_become: false`, `ansible_python_interpreter: /usr/bin/python3` on the FW host.

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

## 5. Secrets — HashiCorp Vault is the store

Secrets are **not** kept in ansible-vault files. Every role/play that needs one goes through
Vault (KV v2, mount `secret`, per-env prefix `{platform_env}/…`):

- `roles/vault_login` — authenticates as the `ansible-deploy` AppRole (creds file
  `secrets/app-vault-approle-ansible-deploy.json`); the retired root token is never used
  (fails loudly instead of falling back).
- `roles/vault_secret` — get-or-create ONE KV path (`vault_secret_path` + `vault_secret_init`),
  read-only when `init` is empty, rotation via `vault_secret_force_fields`.
- Service-specific readers (e.g. `roles/opnsense_api_creds`) publish the values as facts;
  nothing is printed (`no_log`), nothing lands in git.

The only secrets allowed outside Vault are Vault's own bootstrap (unseal keys — kept
off-platform) and the controller's local mirrors under `~/.openclaw/workspace/infra/secrets/`
(0600, synced by `playbooks/secrets-to-vault.yml`, validated by `playbooks/secrets-validate.yml`).

## 6. OPNsense API Authentication

Both OPNsense collections authenticate with an API key (never SSH). The key belongs to the
contract-named automation account **`svc-ansible-prod`** and is **minted through the MVC API,
never in the UI and never baked into the seed**:

```bash
# get-or-mint: reuse the token from Vault if it still works, otherwise mint one with the
# seeded break-glass genesis credential (oob-admin) and store it — also rotates after a reseed
ansible-playbook -i inventories/<env> playbooks/opnsense-api-bootstrap.yml
```

The token lives in Vault at `secret/{platform_env}/opnsense/api` (fields `key`, `secret`);
every FW play starts with `roles/opnsense_api_creds`, which reads that path (or the env's
local fast-path file) and publishes `opn_key` / `opn_secret` / `opnsense_api_key` /
`opnsense_api_secret`. Nothing is stored in `vault.yml` and nothing is typed into the GUI.

```yaml
# inventories/<env>/group_vars/opnsense.yml (catalog + connection; no secrets)
opn_host: 10.6.239.196
opn_port: 443
opnsense_api_bootstrap_genesis_file: ".../secrets/fabric/net-opnsense-<env>-oob-admin.json"
```

## 7. Idempotency — ensure() pattern

Every Ansible task against OPNsense **must be idempotent**. The `by_systems.opnsense` + `ansibleguy.opnsense` modules follow a consistent pattern:

```yaml
- name: Ensure a Kea DHCPv4 reservation (catalog-driven, lib-opnsense underneath)
  by_systems.opnsense.opnsense_kea4_reservation:
    host: "{{ opn_host }}"
    key: "{{ opnsense_api_key }}"
    secret: "{{ opnsense_api_secret }}"
    ip_address: "10.1.1.50"
    hw_address: "bc:24:11:00:00:01"
    state: present
```

- Use `state: present` / `state: absent` — never raw API calls in playbooks (`uri` only for read-only lookups/probes where no module exists)
- No `shell:` or `command:` tasks for OPNsense config — always use a collection module
- Ownership split: the **seed** owns L2/L3 topology, system identity, interface settings and gateways (no MVC setter for interface addressing); **Ansible** owns every MVC-managed service (rules, aliases, NAT, DNS, DHCP, syslog, chrony, monit, …) from the catalog in `group_vars/opnsense.yml`. Retired duplicates: `roles/opnsense/tasks/_archive/`, `playbooks/_archive/`.

## 8. Running Playbooks

```bash
source ~/.venv/ansible/bin/activate

# 1) API token (get-or-mint → Vault; rotates itself after a reseed)
ansible-playbook -i inventories/<env> playbooks/opnsense-api-bootstrap.yml

# 2) Full OPNsense config from the catalog — ALWAYS dry-run first
ansible-playbook -i inventories/<env> playbooks/opnsense.yml --check --diff -e opn_fw_confirm_full=true
ansible-playbook -i inventories/<env> playbooks/opnsense.yml -e opn_fw_confirm_full=true

# One concern only (rules / aliases / NAT by description or alias name)
ansible-playbook -i inventories/<env> playbooks/opnsense.yml -e '{"opn_fw_only": ["<descr>"]}'

# Tag subsets
ansible-playbook -i inventories/<env> playbooks/opnsense.yml --tags firewall
```

## 9. Verify

```bash
# Functional health gate (SVC-51: must be green twice after seed + Ansible)
scripts/fw_verify_health.py --secret-file ~/.openclaw/workspace/infra/secrets/fabric/net-opnsense-<env>-svc-ansible.json --expect-wan2

# Hardware drift gate for the FW VM (seed pipeline, read-only)
python3 ../infra-terraform-proxmox/modules/vm-opnsense/seed/recreate-and-seed.py vm-opns-01 --check
```

## References

- Collection docs: <https://github.com/ansibleguy/collection_opnsense> · `by_systems.opnsense` = <https://github.com/by-openclaw/ansible-opnsense> (lib-opnsense)
- `roles/opnsense/README.md` — role contract and variables
- ADR-0015: Network/VLAN architecture
- ADR-0024: Identity provisioning pattern (vault → HashiVault migration path)
