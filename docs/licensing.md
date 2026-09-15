# Third-party licensing (BoM)

Every component this platform deploys or depends on, with its SPDX identifier, class and owner, per
`doc-platform-core` ADR `security/0005-licensing-policy` §7. **This file is about other people's code.
Our own code is MIT — see [`LICENSE`](../LICENSE) at the repo root** (same for `lib-opnsense`,
`ansible-opnsense`, `infra-terraform-proxmox`, `doc-platform-core`).

- **Class** — `Approved` (ADR §2, deploy freely) or `Flagged` (ADR §3, needs a written assessment;
  every flagged component below already has one in ADR §4).
- **Owner** — the role or repo that owns the version pin. Whoever bumps the pin updates the row in the
  same PR (ADR §6). Accountable owner for every licence decision: @yboujraf.
- **What we may do** with each class is the permission matrix in ADR §5. Short version: deploy, expose
  internally, configure and keep our glue private — all classes. Modify an AGPL tool and serve it, host
  any of this **for a customer**, or resell it — stop and get a review.
- **Last reviewed:** 2026-09-09. Cadence: annually, plus immediately on any upstream relicense (ADR §8).

Firewall package versions and licences below are read from the appliance itself
(`core/firmware/info`, test FW 26.7.3); service versions are the pins in this repository.

## Firewall (OPNsense appliance) — owner `roles/opnsense` + `infra-terraform-proxmox/modules/vm-opnsense`

| Component | Version | SPDX | Class | Role on the firewall |
|---|---|---|---|---|
| OPNsense | 26.7.3 (test) / 26.1.9 (prod) | `BSD-2-Clause` | Approved | firewall OS, WebGUI, MVC API |
| Suricata | 8.0.6 | `GPL-2.0` | Approved | IDS, alert-only on WAN, feeds CrowdSec |
| CrowdSec agent + firewall bouncer | 1.7.8 / 0.0.34 | `MIT` | Approved | IPS enforcement (`os-crowdsec`) |
| Unbound | 1.26.0 | `BSD-3-Clause` | Approved | resolver, split-DNS |
| dnscrypt-proxy | 2.1.15 | `ISC` | Approved | encrypted upstream DNS |
| Kea DHCP | 3.0.4 | `MPL-2.0` | Approved | DHCPv4 / DHCPv6 |
| radvd | 2.20 | `BSD-3-Clause` (RADVD variant) | Approved | IPv6 router advertisements |
| dnsmasq | 2.93 | `GPL-2.0` | Approved | present, kept off by the catalog |
| chrony | 4.8 | `GPL-2.0` | Approved | time sync (the legacy ntpd stays stopped) |
| Monit | 6.0.0 | `AGPL-3.0` | **Flagged** (ADR §4 blanket) | process alerts to Mailcow |
| lldpd | 1.0.21 | `ISC` | Approved | LLDP |
| acme.sh | 3.1.4 | `GPL-3.0-or-later` | Approved | Let's Encrypt client (`os-acme-client`) |
| ddclient | 3.11.2 | `GPL-2.0-or-later` | Approved | Cloudflare DynDNS |
| mdns-repeater | 1.11 | `GPL-2.0` | Approved | mDNS across zones |
| qemu-guest-agent | 11.1.0 | `GPL-2.0` | Approved | Proxmox integration |
| syslog-ng | 4.12.0 | `GPL-2.0-or-later`, `LGPL-2.1-or-later` | Approved | remote syslog to Loki and CrowdSec |
| strongSwan | 6.0.7 | `GPL-2.0` | Approved | IPsec, present and unused |
| OpenSSH | 10.5p1 | `BSD-3-Clause` (OpenSSH) | Approved | management SSH |
| Python | 3.13 | `PSF-2.0` | Approved | appliance scripting runtime |
| `os-*` plugins (acme-client, chrony, crowdsec, ddclient, dnscrypt-proxy, lldpd, mdns-repeater, qemu-guest-agent) | catalog pins | `BSD-2-Clause` | Approved | plugin glue |

## Automation — owner `ansible-platform`, `lib-opnsense`, `ansible-opnsense`

| Component | Version | SPDX | Class | Role |
|---|---|---|---|---|
| ansible-core | 2.20 | `GPL-3.0` | Approved | provisioning engine |
| community.general, ansible.posix, community.postgresql, community.docker, community.crypto | exact pins in `requirements.yml` | `GPL-3.0` | Approved | collections |
| `lib-opnsense` (ours) | git pin | `MIT` | Approved | OPNsense API managers |
| `by_systems.opnsense` (ours) | git pin | `MIT` | Approved | Ansible modules over lib-opnsense |
| Terraform | 1.14.8 | `BUSL-1.1` | **Flagged** (ADR §4, approved 2026-09-09) | VM / LXC / SDN provisioning; migration target OpenTofu (`MPL-2.0`) |
| bpg/proxmox provider | 0.100 | `MPL-2.0` | Approved | Terraform provider |

## Platform services

| Service | Version (pin) | SPDX | Class | Owner (role) |
|---|---|---|---|---|
| Proxmox VE / Backup Server | node / `vm-pbs-01` | `AGPL-3.0` | **Flagged** (§4 blanket) | `infra-terraform-proxmox`, `roles/pbs` |
| HashiCorp Vault | 2.0.4 | `BUSL-1.1` | **Flagged** (§4, approved) | `roles/vault` |
| Authentik | `roles/authentik` pin | `MIT` | Approved | `roles/authentik` |
| Traefik | v3.7.11 | `MIT` | Approved | `roles/traefik` |
| AdGuard Home | 0.107.79 | `GPL-3.0` | Approved | `roles/adguard` |
| CrowdSec LAPI | 1.7.8 | `MIT` | Approved | `roles/crowdsec` |
| GitLab CE | 19.3.0 | `MIT` (CE edition) | Approved | `roles/gitlab` |
| Harbor | v2.12.2 | `Apache-2.0` | Approved | `roles/harbor` |
| Verdaccio | 6.9.3 | `MIT` | Approved | `roles/verdaccio` |
| Nextcloud | 34.0.3 | `AGPL-3.0` | **Flagged** (§4 blanket) | `roles/nextcloud` |
| Mailcow | 2026-05c | `GPL-3.0` | Approved | `roles/mailcow` |
| NetBird | v2.39.0 | `BSD-3-Clause` | Approved | `roles/netbird` |
| NetBox | v4.6.8 | `Apache-2.0` | Approved | `roles/netbox` |
| JumpServer CE | v4.10.19 | `GPL-3.0` | Approved | `roles/jumpserver` |
| Vaultwarden | 1.37.1 | `AGPL-3.0` | **Flagged** (§4 blanket) | `roles/vaultwarden` |
| Loki | `roles/loki` pin | `AGPL-3.0` | **Flagged** (§4 blanket) | `roles/loki` |
| Promtail | `roles/promtail` pin | `AGPL-3.0` | **Flagged** (§4 blanket) | `roles/promtail` |
| Grafana | `roles/grafana` pin | `AGPL-3.0` | **Flagged** (§4 blanket) | `roles/grafana` |
| Prometheus | `roles/prometheus` pin | `Apache-2.0` | Approved | `roles/prometheus` |
| SeaweedFS | 4.44 | `Apache-2.0` | Approved | `roles/seaweedfs` |
| step-ca | `roles/stepca` pin | `Apache-2.0` | Approved | `roles/stepca` |
| PostgreSQL | `roles/postgres` pin | `PostgreSQL` | Approved | `roles/postgres` |
| pgAdmin 4 | 9.17 | `PostgreSQL` | Approved | `roles/pgadmin` |
| Redis | 8.10.0 | `AGPL-3.0` (its tri-licence's OSI option; the others are `RSAL-v2` / `SSPL-1.0`) | **Flagged** (§4 blanket) | `roles/redis` |
| Docker Engine | distro pin | `Apache-2.0` | Approved | the roles that run containers |

## Dependencies worth recording

ADR §6: a dependency gets its own line only when its licence class is **different or stricter** than the
component that pulls it in. Transitive library graphs are not enumerated here — they live in the repo's
pins and in the upstream container manifests.

| Component | Dependency | Why it is recorded |
|---|---|---|
| Authentik, NetBox, Nextcloud, Harbor, GitLab | Redis (`AGPL-3.0`), PostgreSQL (`PostgreSQL`) | the datastore is flagged while the service itself is not |
| Traefik (`MIT`) | CrowdSec bouncer (`MIT`), acme.sh path on the firewall (`GPL-3.0-or-later`) | GPL tooling invoked from a permissive service |
| Our Ansible roles (`MIT`) | ansible-core and collections (`GPL-3.0`) | our MIT code runs on a GPL engine; no linking, no distribution |

## Rules

- A component enters the platform only with a row here and an SPDX identifier — never "open source".
- The pin and the row change in the same PR, so a relicense is caught at upgrade time (ADR §8).
- Flagged components are all covered by ADR §4; a **new** flagged licence needs its own assessment issue
  in `doc-platform-core` before deployment.
- The moment anything here is modified and served over a network, or deployed for a customer, the
  matrix in ADR §5 stops applying and the decision goes back to @yboujraf.
