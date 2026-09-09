# Role: opnsense

Applies the per-env **FW catalog** (`inventories/<env>/group_vars/opnsense.yml`) to OPNsense through
the REST/MVC API using `by_systems.opnsense` modules (lib-opnsense managers underneath). Every catalog
key has a consumer task file; the role has **no raw API writer** (`uri` appears only for read-only
lookups where no module exists) and no shell/command task.

Ownership split: the **seed** (infra-terraform-proxmox `modules/vm-opnsense/seed`) owns L2/L3 topology,
system identity, interface settings, gateways and the NetFlow exporter; **Ansible** owns every
MVC-managed service below. Firmware updates/upgrades are a deliberate per-env window, never part of a
converge.

## Contract

- **Idempotent:** every task is an `ensure()` (`state: present/absent` or a singleton settings block);
  a second run is `changed=0`. Proven on the test FW after every block (see the PRs in `#301`).
- **Catalog → PR → apply is the only way state reaches a firewall** — test FW included. A knob the
  catalog does not manage may not be touched by hand; if a value must be owned, declare it here first
  (default = OPNsense default) so the converge removes any drift.
- **Both directions:** an unscoped run ends with the prune report (firewall family); `-e opn_prune=true`
  deletes what the catalog stopped declaring (SVC-47). Other families: #316.
- **No secrets in the catalog.** The API token is minted by `playbooks/opnsense-api-bootstrap.yml`
  (get-or-mint → Vault `secret/{env}/opnsense/api`) and published by `roles/opnsense_api_creds`;
  Monit's SMTP credentials come from Vault via the playbook's pre-play.
- **Check mode works** for every task (`--check --diff`); read-only lookups run under `--check`.

## What it configures (order = `tasks/main.yml`)

| Tag(s) | Task file | Catalog keys | Modules |
|---|---|---|---|
| `firmware`, `plugins` | `firmware.yml` | `opnsense_plugins`, `opnsense_firmware_{target,upgrade}` | `opnsense_firmware` (check → report; gated apply + wait for the target version), `opnsense_plugin` (job-log verdict) |
| `gateway` | `gateways.yml` | `opnsense_proximus_monitor_{v4,v6}`, `opn_gateways` | `opnsense_rt_gateway`: monitors of the DYNAMIC Proximus gateways the FW has (read-only lookup first) + the static gateways the catalog declares (e.g. the prod FW OOB next hop on test) |
| `routes` | `routes.yml` | `opn_routes` | `opnsense_rt_route` (static routes by gateway NAME; runs after gateways) |
| `dns`, `dnscrypt` | `dnscrypt.yml` | `opn_dnscrypt_proxy` | `opnsense_dnscrypt_settings` (listeners, filters, serverlist), `opnsense_dnscrypt_service` |
| `dns`, `unbound` | `dns.yml` | `opnsense_unbound_*` | `opnsense_ub_settings` (enable — a seeded FW ships Unbound off; `noregrecords` so the asset FQDN is the explicit override, NAM-06/08), `opnsense_ub_forward` (catch-all → dnscrypt), `opnsense_ub_dot` (purge), `opnsense_ub_service` |
| `dyndns` | `dyndns.yml` | `opnsense_dyndns_accounts` | `opnsense_ddns_account`, `opnsense_ddns_service` (restart on change) |
| `ntp`, `chrony` | `chrony.yml` | `opnsense_chrony_*` | `opnsense_chrony_settings`, `opnsense_chrony_service`, `opnsense_core_service` (legacy `ntpd` stopped) |
| `ids` | `ids.yml` | `opn_ids` | `opnsense_ids_settings` (mode, interfaces, HOME_NET from the catalog group, EVE → syslog, `mpm_algo`, `detect_profile`), `opnsense_ids_ruleset`, `opnsense_ids_service` |
| `mdns` | `mdns.yml` | `opn_mdns` | `opnsense_mdnsrepeater_settings`, `opnsense_mdnsrepeater_service` (skips with a note while the plugin is only previewed under `--check`) |
| `acme`, `certs` | `acme.yml` | `opn_acme` + Vault `prod/cloudflare/<zone>` | `opnsense_acme_settings/_account (registered)/_validation (DNS-01 Cloudflare)/_action (restart WebGUI)/_certificate (`issued` once; `-e opn_acme_renew=true` renews)/_service` |
| `dhcp`, `kea`, `radvd`, `dnsmasq` | `dhcp.yml` | `opn_kea_dhcp4`, `opn_kea_dhcp6`, `opn_radvd`, `opn_dnsmasq` | `opnsense_kea4/6_settings`, `opnsense_kea4/6_subnet` (with `option_data`), `opnsense_kea_service`, `opnsense_radvd_entry/_service`, `opnsense_dnsmasq_settings/_service` (kept off) |
| `services`, `lldpd` | `lldpd.yml` | `opnsense_lldpd_*` | `opnsense_lldpd_settings`, `opnsense_lldpd_service` |
| `firewall`, `aliases` | `aliases.yml` | `opn_aliases` | `opnsense_fw_alias` |
| `firewall`, `rules` | `rules.yml` | `opn_filter_rules` | catalog lint gate (`files/catalog_lint.py` §1a/§3/§4/twins) then `opnsense_fw_filter` |
| `firewall`, `nat` | `nat.yml` | `opn_dnat_rules`, `opn_snat_rules` | `opnsense_fw_dnat`, `opnsense_fw_source_nat` |
| `services` | `services.yml` | — | `opnsense_qemuguestagent_settings/_service`, `opnsense_crowdsec_service`, `opnsense_netflow_service` (reconfigure only; config is seed-owned) |
| `services`, `monit` | `monit.yml` | `opnsense_monit_*` + Vault SMTP | `opnsense_monit_settings/_alert/_test/_service` (`ProcessDown` is `type: Custom`) |
| `syslog` | `syslog.yml` | `opnsense_syslog_*` | `opnsense_syslog_dest` |
| `firewall`, `prune` | `prune.yml` | `opn_prune` (+ the four object lists) | read-only lookups → marker-bearing aliases/rules/DNAT/SNAT the catalog does not declare: reported always, deleted through the same modules (`state: absent`) only with `-e opn_prune=true` on an unscoped run |

Archived (never delete): `tasks/_archive/` (system, interfaces, wan2, dhcp legacy, ntp, qemu-agent,
install_plugin) — superseded by the seed or by the modules above.

## Gotchas the tasks encode

- A fresh 26.7.0 nano **refuses every plugin install** until its point update; the firmware backend
  still answers `done` — `opnsense_plugin` reads the job log and fails loudly with the window command.
- Interface names in the catalog are friendly (`mgmt`, `dmz`, `wan`, …) and resolve to slot ids through
  `opnsense_iface_lookup` (`opn_interface_map`); the seed never assigns a `wan` slot.
- IDS: a seeded FW stores `interfaces=wan` (invalid) and refuses every IDS save — settings go first.
  Suricata 8.0.6 with ET Open sits at ~3.9 GiB RSS once loaded: the FW VM profile is **8 GiB**
  (seed `vm.memory`, infra-terraform-proxmox #91); on a 3 GiB VM it is OOM-killed and the catalog
  must keep `opn_ids.enabled: false` until the VM is resized (ansible-platform #310).
- ACME: the plugin's auto-renewal needs its cron job — `acmeclient/settings` saved through the API with
  `autoRenewal=1` + service reconfigure creates it (prod had `autoRenewal=1` and NO cron → the GUI
  certificate ran to 2 days before expiry, 2026-09-09). Issuance = `state: issued` (once; the plugin signs
  asynchronously — the module waits for the terminal status). The WebGUI binding
  (`system.webgui.ssl-certref`) has no MVC endpoint and the plugin's `certRefId` is read-only on the
  API → seed concern (pre-set refid), tracked on #317; prod's GUI already serves the ACME leaf.
- Kea6 subnets need their interface selected in Kea6 *general* first; Kea options (`option_data`)
  converge sub-key by sub-key (lib-opnsense #104).

## Usage

```bash
# Full catalog — ALWAYS dry-run first
ansible-playbook -i inventories/<env> playbooks/opnsense.yml --check --diff -e opn_fw_confirm_full=true
ansible-playbook -i inventories/<env> playbooks/opnsense.yml -e opn_fw_confirm_full=true

# One block
ansible-playbook -i inventories/<env> playbooks/opnsense.yml --tags dns
ansible-playbook -i inventories/<env> playbooks/opnsense.yml --tags dhcp,ids,mdns

# Firmware window (deliberate; reboots the FW; run the PVE snapshot first)
ansible-playbook -i inventories/<env> playbooks/opnsense.yml --tags firmware \
  -e opnsense_firmware_upgrade=true -e opnsense_firmware_target=<version>

# Health gate — must be green twice after every apply
scripts/fw_verify_health.py --secret-file <creds.json> --expect-wan2 [--no-proximus] [--no-kea]
```

## References

- `docs/setup.md` — Vault, API bootstrap, seed ownership, playbooks, verify
- `docs/services/opnsense.md` — setup runbook (19 sections) · `docs/licensing.md` — licence BoM
- ADRs: services/0001 (provisioning), services/0006 (IDS, Internet-by-request), naming/0003 (aliases/rules), infra/0004 (zones)
- Collections: `by_systems.opnsense` = <https://github.com/by-openclaw/ansible-opnsense> (lib-opnsense)
