# Archived task files (never delete — archive)

Superseded on 2026-09-07 by the ownership split **seed = L2/L3 topology + system identity +
interface settings + gateways; Ansible = every MVC-managed service** (ADR services/0008, the
seed pipeline in infra-terraform-proxmox `modules/vm-opnsense/seed`). Kept for history; **not
included by `main.yml`**, no variables in `defaults/main.yml` feed them.

| File | Why archived |
|---|---|
| `system.yml` | hostname/domain/timezone are rendered by `build-seed.py`; used `puzzle.opnsense` (config.xml edits need root — blocked) |
| `interfaces.yml` | old test-era VLAN model on `vtnet1`; the seed renders VLANs on `vtnet0` + assignments + IPs (no MVC setter for addressing) |
| `wan2.yml` | Telenet gateways (`WAN2GW`/`WAN2GWv6`, monitors, default flags) are now rendered by the seed's gateway generator |
| `dhcp.yml` | ISC-DHCP-on-opt1 model via `puzzle.opnsense`; DHCP is Kea (catalog `opn_kea_dhcp4/6`, lib `dhcp/*` managers) |
| `ntp.yml` | base ntpd via `puzzle.opnsense`; NTP is `os-chrony` (`chrony.yml`) |
| `qemu-agent.yml` | `ansible.builtin.raw` `pkg install`/`sysrc` (needs root SSH; on a `connection: local` host it would run on the controller) — the agent is installed through the firmware API (`os-qemu-guest-agent` in `opnsense_plugins`) and enabled via MVC in `services.yml` |

`puzzle.opnsense` is no longer a dependency (`requirements.yml`).
