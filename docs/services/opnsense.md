# OPNsense firewalls — Setup Runbook

Follows `doc-platform-core/docs/templates/tool-setup-template.md`, adapted to an appliance (no
container, no Traefik route). Two firewalls: **prod** `vm-opns-01` (`<domain>`) and **test**
`vm-opns-test-01` (`test.<domain>`). Everything below is code: the **seed** builds the VM and its
first boot, the **catalog** (`inventories/<env>/group_vars/opnsense.yml`) owns every service.

## 1. Image decision

OPNsense CE **nano** image (`OPNsense-26.7-nano-amd64.raw`, `poc-iso`), imported by the seed pipeline
(`infra-terraform-proxmox/modules/vm-opnsense/seed/recreate-and-seed.py`). Firmware pins per env
(`opnsense_firmware_target`); updates and upgrades are deliberate windows, never part of a converge.
Licences: `docs/licensing.md` §Firewall.

## 2. Services architecture

| Concern | Owner | Where |
|---|---|---|
| VM hardware (2 vCPU, 8 GiB, 5 NICs), L2/L3 topology, interfaces, VLANs, system identity, WAN gateways | seed | `seeds/<fw>.json` + `templates/baseline.xml`; drift gate `--check`, hardware converge `--apply-hw` |
| Aliases, rules, NAT, DNS chain (Unbound → dnscrypt), DHCP (Kea v4/v6, radvd), IDS (Suricata alert-only on WAN), CrowdSec, Monit, ACME, DynDNS, chrony, lldpd, mDNS, syslog, static gateways/routes, plugins | catalog | `roles/opnsense/tasks/*.yml` through `by_systems.opnsense` (lib-opnsense) |
| Zones | ADR infra/0004 | MGMT, DMZ, SVC, VPN, IoT, VoIP, Storage, Media, GAMING, CCTV + OOB, FAB |
| Uplinks | seed | prod: Proximus (PPPoE, default) + Telenet (static /29, mail + services); test: Telenet only (own `.220/::6`) |

DNS chain: AdGuard → Unbound (FW) → dnscrypt-proxy. IPS: CrowdSec (central LAPI, FW bouncer); Suricata
is the WAN sensor (feed to CrowdSec tracked on #326).

## 3. Pre-requisites

- Proxmox node with bridges `vmbrAPPS`, `vmbrOOB`, `vmbrWAN1`, `vmbrWAN2`, `vmbrFAB`; `poc-data` / `poc-iso` storage.
- Vault reachable with the `ansible-deploy` AppRole (`roles/vault_login`); the genesis credential file
  for the env (`secrets/fabric/net-opnsense-<env>-oob-admin.json`, rendered by the seed build).
- Controller: this repo, `requirements.yml` collections (exact pins), lib-opnsense editable or pinned.

## 4. Secrets (Vault KV paths)

| Path | Fields | Written by | Read by |
|---|---|---|---|
| `secret/<env>/opnsense/api` | host, port, username, key, secret (+ metadata `rotated_at`, `reason`) | `playbooks/opnsense-api-bootstrap.yml` (mint/rotate) | `roles/opnsense_api_creds` (every FW play) |
| `secret/<env>/opnsense/oob-admin` | genesis break-glass | seed build | bootstrap (mint only) |
| `secret/prod/mail/opnsense` | address, password, smtp_port | `roles/mailbox` | Monit pre-play (both envs — one Mailcow) |
| `secret/prod/cloudflare/<zone>` | api_token, account_id, zone_id, acme_email | `roles/cloudflare` | ACME pre-play (DNS-01), DynDNS |
| `secret/prod/opnsense/config-backup-age` | age key | `playbooks/opnsense-config-backup.yml` | config export encryption |
| `secret/prod/net/isp-proximus-pppoe` | pppoe_username, pppoe_password (**raw**, as issued; metadata `format=raw`, `rotated_at`, `reason`) | `playbooks/opnsense-pppoe-rotate.yml` (hidden prompt) | seed render (`roles/opnsense_provision`), `roles/opnsense_pppoe` (live apply, base64 in config.xml) |

Rotation: quarterly user timer per env on the controller (`playbooks/opnsense-token-rotation.yml`,
`fw-token-rotation@<env>.timer`; force-rotate + `--tags dns --check` gate). No secret in the catalog.
ISP PPPoE password: portal first, then `playbooks/opnsense-pppoe-rotate.yml` (Vault → firewall over SSH +
wheel sudo, `configctl` re-dial, API waits for the gateway; without sudo the seed applies it at the re-seed).
The fabric fallback file is refreshed *from* Vault by that playbook — never edited by hand.

## 5. Certificates

WebGUI certificate from Let's Encrypt through the catalog (`opn_acme`: account, Cloudflare DNS-01
validation, restart-webgui action, certificate `state: issued`, auto-renewal cron). Prod: `fw.<domain>`
production LE; test: staging. Binding a freshly seeded FW's GUI to the leaf = seed concern (#317).

## 6. Configuration source (instead of an environment file)

`inventories/<env>/group_vars/opnsense.yml` — the catalog. Keys and consumers: `roles/opnsense/README.md`
(task table). Lint gate `roles/opnsense/files/catalog_lint.py` (naming/0003). No environment file exists.

## 7. Provisioning (instead of docker compose)

One command takes a free VMID to a firewall running the whole catalog — no script, no hand steps:

```bash
ansible-playbook -i inventories/test playbooks/opnsense-build.yml -e opnsense_provision_fw=vm-opns-test-01
```

It chains, in the order the 2026-09-21 prod re-seed proved: the VM from the seed profile's hardware
truth → `config.xml` rendered and handed to the boot importer → firmware + plugins with the genesis
credential the provisioning read (Vault sits behind the firewall being built) → the catalog families
that need no Vault secret (after which the SSH hop and Vault are reachable again) → Unbound overrides
→ the svc-ansible token minted into Vault (the service user gets its Vault GUI password, so SSH + sudo
work at once) → the full catalog through Vault → CrowdSec agent + bouncer (a stale LAPI registration
is retired) → config export → proof of both uplink families. Family selection inside `opnsense.yml`
is by variable (`opn_only_families` / `opn_skip_families`). Rebuilding an existing firewall DESTROYS it
and needs `-e opnsense_provision_recreate=true` (prod also `-e opnsense_provision_confirm_prod=true`);
the stages refuse to run against a firewall this run did not create. Parity afterwards:
`playbooks/opnsense.yml --check -e opn_fw_confirm_full=true` → changed=0.

Measured on a throwaway VMID (2026-09-09): **150 s** from nothing to a firewall answering its API
with the seeded identity — 77 s of that is the boot importer. A second run is `changed=0`.

Just the VM and its configuration, without the firmware and catalog phases:

```bash
ansible-playbook -i inventories/test playbooks/opnsense-provision.yml -e opnsense_provision_fw=<fw>
```

Hardware drift on a firewall that is already running (the old Python pipeline, still the path for an
in-place hardware change until it is archived — infra-terraform-proxmox#93):

```
recreate-and-seed.py <fw> --check            # hardware drift, read-only
recreate-and-seed.py <fw> --apply-hw         # memory/cores/onboot/tags in place (prod: --confirm-prod-restart)
```

## 8. Exposure / routing

Admin: OOB (`10.6.239.x`) and the VPN route tiers; WebGUI never on a WAN. Public services: DNAT on the
Telenet WAN only (mail MX 25; TLS-only client ports are deliberately NOT public). Split-DNS host
overrides (`opn_unbound.host_overrides`, `playbooks/opnsense-unbound-overrides.yml`).

## 9. Installation steps

```bash
# One command for all of it (§7):
ansible-playbook -i inventories/test playbooks/opnsense-build.yml -e opnsense_provision_fw=vm-opns-test-01

# …or the same phases one at a time, which is what a dry run needs:
# 1) VM + seeded configuration                 2) API token (get-or-mint → Vault)
ansible-playbook -i inventories/test \
  playbooks/opnsense-provision.yml \           ansible-playbook -i inventories/test playbooks/opnsense-api-bootstrap.yml
  -e opnsense_provision_fw=vm-opns-test-01
# 3) catalog — ALWAYS dry-run first
ansible-playbook -i inventories/test playbooks/opnsense.yml --check --diff -e opn_fw_confirm_full=true
ansible-playbook -i inventories/test playbooks/opnsense.yml -e opn_fw_confirm_full=true
ansible-playbook -i inventories/test playbooks/opnsense-unbound-overrides.yml
# 4) health gate — must be green twice
scripts/fw_verify_health.py --secret-file <creds.json> --expect-wan2 [--no-proximus]
```
Prod: same commands, each in a deliberate window (#307), read-only `--check` first.

## 10. Post-install configuration

Firmware window (`--tags firmware -e opnsense_firmware_upgrade=true -e opnsense_firmware_target=<v>`,
snapshot first); IDS on (`opn_ids.enabled`, needs the 8 GiB profile); Monit alerts (mailbox secret);
scheduled token rotation timer; prune report (`-e opn_prune=true` deletes what the catalog stopped declaring).

## 11. Upgrade procedure

1. PVE snapshot. 2. `--tags firmware` check (report only). 3. Firmware window command with the target
version. 4. Plugins re-checked by the same tag. 5. Full catalog `--check` then apply; health gate ×2.
Prod = window. Major upgrades (26.1 → 26.7): reseed with the new nano image, not in place.

## 12. Health checks

`scripts/fw_verify_health.py` (25 checks: API, interfaces, gateways, services, DNS chain, Kea, WAN2),
second catalog run `changed=0`, `core/service/search` (all services running except ntpd), Monit
process checks, CrowdSec LAPI decisions, syslog stream in Loki (`{job="opnsense"}`).

## 13. Troubleshooting

`roles/opnsense/README.md` §Gotchas (plugin refusal on 26.7.0, IDS `interfaces=wan`, Suricata
memory, ACME async sign / cron / certRefId, Monit reconfigure vs daemon, Kea6 interface first,
ntpd via `system.timeservers`).

## 14. Identity and access

Automation: `svc-ansible-<env>` (today `svc-ansible-prod` on both — infra #89) with one API key,
`admins` group, minted by the bootstrap. Humans: `by-research` break-glass (`oob-admin` genesis, naming
under review infra #89); SSH by key only (`id_ed25519_opnsense`), root blocked. SSO: Authentik LDAP
outpost pending (SSO tracker). Access is group-based, never per person.

## 15. Notifications

Monit → Mailcow service mailbox → `alerts@<domain>` (subject `[<fw>] $SERVICE $EVENT`); CrowdSec
decisions visible on the LAPI; syslog → Loki (`audit="true"`); firmware/ACME state through the
playbook reports. Alertmanager/dashboards: monitoring track (parked).

## 16. Backup and restore

`playbooks/opnsense-config-backup.yml`: config.xml export, age-encrypted, to the NAS share (`/mnt/pve/poc-backup/…`)
+ PBS VM backup (fs-freeze off). Restore = reseed + bootstrap + catalog (config is code), or PBS
restore of the VM for a like-for-like rollback. Snapshots before every firmware window.

## 17. Logging and audit

syslog-ng → promtail listener on `lxc-monitoring-01` (`{job="opnsense", audit="true"}`), 90-day
retention (Loki `2160h`, queries may span it). IDS EVE → syslog. Config changes: git history of the
catalog + Vault audit of the credentials.

## 18. Decommission

Prod FW is Layer 0 — decommission = replacement window only. Test FW: `recreate-and-seed.py` recreates
it at will; the catalog and Vault path stay. `roles/service_decommission` applies to guests, not FWs.

## 19. Licensing

`docs/licensing.md` §Firewall (OPNsense `BSD-2-Clause`, Suricata `GPL-2.0`, Monit `AGPL-3.0` — flagged, covered by the blanket in ADR security/0005 §4). Our own code is MIT in `LICENSE`.

## References

- `roles/opnsense/README.md`, `docs/setup.md`, `docs/audits/opnsense-2026-09-07.md`, tracker #324
- ADRs: services/0001 (provisioning), services/0006 (IDS/IBR), services/0010 (CrowdSec), naming/0003, infra/0004, security/0004
- infra-terraform-proxmox `modules/vm-opnsense/seed/` (seed pipeline), lib-opnsense, ansible-opnsense
