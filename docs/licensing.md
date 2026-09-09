# Licensing inventory (BoM)

The platform's licence Bill of Materials per `doc-platform-core/docs/standards/licensing-standard.md`:
every deployed component with its **SPDX identifier**, its class under the standard (Approved /
**Flagged**), and the approval state. Versions are the pins in this repository on 2026-09-09; the
firewall package licences come from the appliance itself (`core/firmware/info`, test FW 26.7.3).
Update the row in the same PR as the pin. A component without a row does not get deployed (SEC-35).

**Flagged = written approval from @yboujraf required (standard §Flagged).** Today the platform runs
several flagged components with **no approval record on file** — listed in §Flagged below; that is the
open licensing finding (SEC-36), not something this document can close.

## Firewall (OPNsense appliance)

| Component | Version | SPDX | Class | Role |
|---|---|---|---|---|
| OPNsense | 26.7.3 (test) / 26.1.9 (prod) | BSD-2-Clause | Approved | firewall OS + WebGUI/MVC |
| Suricata | 8.0.6 | GPL-2.0 | Approved | IDS alert-only on WAN, feeds CrowdSec |
| CrowdSec agent + firewall bouncer | 1.7.8 / 0.0.34 | MIT | Approved | IPS enforcement (os-crowdsec) |
| Unbound | 1.26.0 | BSD-3-Clause | Approved | resolver, split-DNS |
| dnscrypt-proxy | 2.1.15 | ISC | Approved (permissive, not yet in the standard's table) | encrypted upstream DNS |
| Kea DHCP | 3.0.4 | MPL-2.0 | Approved | DHCPv4/v6 |
| radvd | 2.20 | BSD-style (RADVD) | Approved (permissive) | IPv6 RA |
| dnsmasq | 2.93 | GPL-2.0 | Approved | present, kept off |
| chrony | 4.8 | GPL-2.0 | Approved | time sync |
| Monit | 6.0.0 | **AGPL-3.0** | **Flagged** | process alerts → Mailcow |
| lldpd | 1.0.21 | ISC | Approved (permissive) | LLDP |
| acme.sh | 3.1.4 | GPL-3.0-or-later | Approved | Let's Encrypt client |
| ddclient | 3.11.2 | GPL-2.0-or-later | Approved | Cloudflare DynDNS |
| mdns-repeater | 1.11 | GPL-2.0 | Approved | mDNS across zones |
| qemu-guest-agent | 11.1.0 | GPL-2.0 | Approved | Proxmox integration |
| syslog-ng | 4.12.0 | GPL-2.0-or-later / LGPL-2.1-or-later | Approved | remote syslog → Loki |
| strongSwan | 6.0.7 | GPL-2.0 | Approved | IPsec, present unused |
| OpenSSH | 10.5p1 | BSD (OpenSSH) | Approved (permissive) | management SSH |
| Python | 3.13 | PSF-2.0 | Approved (permissive) | appliance scripting |
| `os-*` plugins (acme-client, chrony, crowdsec, ddclient, dnscrypt-proxy, lldpd, mdns-repeater, qemu-guest-agent) | catalog pins | BSD-2-Clause | Approved | plugin glue |

## Automation

| Component | Version | SPDX | Class | Role |
|---|---|---|---|---|
| ansible-core | 2.20 | GPL-3.0 | Approved | provisioning |
| community.general / ansible.posix / community.postgresql / community.docker / community.crypto | `requirements.yml` pins | GPL-3.0 | Approved | collections |
| lib-opnsense (ours) | git pin | MIT | Approved | OPNsense API managers |
| by_systems.opnsense (ours) | git pin | MIT | Approved | Ansible modules |
| Terraform | 1.14.8 | **BUSL-1.1** | **Flagged** | VM/LXC/SDN (infra-terraform-proxmox); OpenTofu is the MPL-2.0 successor |
| bpg/proxmox provider | 0.100 | MPL-2.0 | Approved | Terraform provider |

## Platform services

| Service | Version (pin) | SPDX | Class | Notes |
|---|---|---|---|---|
| Proxmox VE / Backup Server | node / vm-pbs-01 | **AGPL-3.0** | **Flagged** | hypervisor, backups (unmodified) |
| HashiCorp Vault | 2.0.4 | **BUSL-1.1** | **Flagged** (listed in the standard) | secrets; OpenBao is the MPL-2.0 successor |
| Authentik | `roles/authentik` pin | MIT | Approved | SSO |
| Traefik | v3.7.11 | MIT | Approved | TLS edge |
| AdGuard Home | 0.107.79 | GPL-3.0 | Approved | DNS filter |
| CrowdSec LAPI | 1.7.8 | MIT | Approved | central decisions |
| GitLab CE | 19.3.0 | MIT (CE edition) | Approved | SCM/CI/registry/Pages |
| Harbor | v2.12.2 | Apache-2.0 | Approved | registry |
| Verdaccio | 6.9.3 | MIT | Approved | npm registry |
| Nextcloud | 34.0.3 | **AGPL-3.0** | **Flagged** | files/contacts (unmodified) |
| Mailcow | 2026-05c | GPL-3.0 | Approved | mail |
| NetBird | v2.39.0 | BSD-3-Clause | Approved | VPN |
| NetBox | v4.6.8 | Apache-2.0 | Approved | CMDB |
| JumpServer CE | v4.10.19 | GPL-3.0 | Approved | bastion |
| Vaultwarden | 1.37.1 | **AGPL-3.0** | **Flagged** | password manager (unmodified) |
| Loki + Promtail | `roles/loki` / `roles/promtail` pins | **AGPL-3.0** | **Flagged** | logs (unmodified) |
| Grafana | `roles/grafana` pin | **AGPL-3.0** | **Flagged** | dashboards (unmodified) |
| Prometheus | `roles/prometheus` pin | Apache-2.0 | Approved | metrics |
| SeaweedFS | 4.44 | Apache-2.0 | Approved | S3 |
| step-ca | `roles/stepca` pin | Apache-2.0 | Approved | internal CA |
| PostgreSQL | `roles/postgres` pin | PostgreSQL | Approved (permissive) | databases |
| pgAdmin 4 | 9.17 | PostgreSQL | Approved (permissive) | DB admin |
| Redis | 8.10.0 | **AGPL-3.0** (tri-licence RSALv2 / SSPL-1.0 / AGPL-3.0 since 8.0; AGPL is the OSI option) | **Flagged** (the standard lists Redis ≥ 7.4) | cache |
| Docker Engine | distro pin | Apache-2.0 | Approved | container runtime |

## Flagged — approval state (standard §Flagged, SEC-36)

| Component | SPDX | Approval on file | What the licence means for us |
|---|---|---|---|
| Vault | BUSL-1.1 | **none** | internal use fine; must not be offered as a competing hosted service |
| Terraform | BUSL-1.1 | **none** | same as Vault; OpenTofu is the drop-in alternative |
| Redis 8 | AGPL-3.0 option | **none** | used unmodified as a network service → no disclosure duty |
| Nextcloud, Grafana, Loki, Promtail, Vaultwarden, Monit, Proxmox VE/PBS | AGPL-3.0 | **none** | used unmodified → no disclosure duty; any modification we run must be published |

The standard requires written approval from @yboujraf for each row above before adoption; they are
already in production. Proposal: one approval record (`docs/licensing-approvals.md`, one line per
component, date, signer) closes the finding; or the ADR-0022 stub is finalised with a blanket rule
"AGPL unmodified as a network service = approved by default". Decision: @yboujraf.

## Rules

- A component enters only with a row here (SPDX identifier populated).
- Licence changes are caught at upgrade time (the pin and this row change in the same PR).
- Our own code (lib-opnsense, ansible-opnsense, this repository) is MIT.
