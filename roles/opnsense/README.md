# Role: opnsense

Configures OPNsense via the REST/MVC API using `ansibleguy.opnsense` (rules/aliases — ADR-mandated) and `by_systems.opnsense` (lib-opnsense MVC: NAT, syslog, …). L2/L3 topology, system identity, interface settings and gateways are SEED-owned (infra-terraform-proxmox `modules/vm-opnsense/seed`).

## Contract

- **Idempotent:** every task uses `state: present/absent`. Safe to run repeatedly.
- **No shell/command tasks.** All config via collection modules only.
- **No hardcoded values in tasks.** All values from `defaults/main.yml` or vault.
- **Bootstrap:** identity + interfaces come from the seed; the svc-ansible API token is minted by `playbooks/opnsense-api-bootstrap.yml` (get-or-mint → Vault; `opnsense-bootstrap.yml` archived under playbooks/_archive). Historic note: it used `uri` for 2 one-shot tasks (hostname + WAN IP) that have no collection module. Guarded by `changed_when`.

## What it configures

| Tag | Task file | What |
|---|---|---|
| `system` | `system.yml` | Hostname, domain, timezone |
| `interfaces` | `interfaces.yml` | WAN static IP, VLAN 310/320/330 on vtnet1 |
| `dns` | `dns.yml` | Unbound enabled, DoT upstream (1.1.1.1, 9.9.9.9) |
| `dhcp` | `dhcp.yml` | DHCP on MGMT (10.1.1.100-199) |
| `ntp` | `ntp.yml` | NTP server (pool.ntp.org upstream) |
| `aliases` | `aliases.yml` | Named firewall aliases (no hardcoded IPs in rules) |
| `rules` | `rules.yml` | NAT, WireGuard WAN allow, VPN→MGMT/SVC |
| `wireguard` | `wireguard.yml` | WireGuard server + peers |

## Variables

See `defaults/main.yml` for all variables with descriptions.

Key variables:

| Variable | Default | Description |
|---|---|---|
| `opnsense_host` | `10.1.1.1` | OPNsense MGMT IP |
| `opnsense_verify_ssl` | `false` | SSL verify (intentional — ADR-0014) |
| `opnsense_hostname` | `vm-opnsense-01` | System hostname (non-prod carries env — set in defaults/main.yml per deployment) |
| `opnsense_domain` | `by-research.be` | System domain |
| `opnsense_wireguard_peers` | see defaults | List of WireGuard peer devices |

## Secrets (via vault)

All secrets must be in `infra/secrets/vault.yml` (ansible-vault encrypted):

```yaml
vault_opnsense_api_key: "<svc-rune API key>"
vault_opnsense_api_secret: "<svc-rune API secret>"
vault_opnsense_wireguard_private_key: "<server private key>"
vault_wg_peer_yboujraf_win11_pubkey: "<Win11 public key>"
vault_wg_peer_yboujraf_mobile_pubkey: "<mobile public key>"
vault_wg_peer_rune_vm_pubkey: "<Rune VM public key>"
```

## Usage

```bash
# Full config
ansible-playbook playbooks/opnsense.yml

# Specific subsystem
ansible-playbook playbooks/opnsense.yml --tags wireguard
ansible-playbook playbooks/opnsense.yml --tags dns,dhcp

# Dry run
ansible-playbook playbooks/opnsense.yml --check --diff
```

## Adding a new WireGuard peer

1. Generate keypair on the new device (e.g. `wg genkey | tee private.key | wg pubkey > public.key`)
2. Add peer entry to `opnsense_wireguard_peers` in `defaults/main.yml`
3. Add `vault_wg_peer_{name}_pubkey` to `infra/secrets/vault.yml`
4. Run: `ansible-playbook playbooks/opnsense.yml --tags wireguard`

## References

- `docs/setup.md` — Ansible install + SSH + vault setup
- ADR-0015: Network/VLAN architecture + WireGuard spec
- Collection docs: <https://github.com/ansibleguy/collection_opnsense> · by_systems.opnsense = <https://github.com/by-openclaw/ansible-opnsense> (lib-opnsense)
