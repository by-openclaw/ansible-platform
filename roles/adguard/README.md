<!--
Copyright (c) BY-SYSTEMS SRL
SPDX-License-Identifier: Apache-2.0
Source: https://github.com/by-openclaw/ansible-platform
-->

# Role: `adguard`

Production-grade, idempotent Ansible reproduction of
`infra-terraform-proxmox/modules/vm-opnsense/seed/setup-adguard-tls.sh`,
parameterized for the **PROD** AdGuard VM `vm-adguard-01` (10.1.x / `fd01:`).

It runs **AdGuard Home** as a container (the pinned official image on the host
network) with a wildcard TLS certificate (DoT / DoH / DoQ), per-VLAN client
policies, and an automatic daily renewal — no WebUI clicks.

## What it does

| Task file     | Purpose |
|---------------|---------|
| `host.yml`    | The host side: systemd-resolved's stub off (frees `:53`). What the host resolves with is `roles/resolver`'s (hardening): a host that runs AdGuard is pointed at the firewall through resolved's uplink list — one writer of `/etc/resolv.conf`. |
| `container.yml` | The container (`adguard_image`, host network, `adguard_home_dir` mounted at the image's conf + work paths, `/etc/lego` read-only); it must answer a query before the retired native unit + binary are removed. |
| `secrets.yml` | Controller-side: read the Cloudflare token + ACME email; read-or-generate the admin bcrypt hash and persist the prod secret JSON back to the controller (`no_log`). |
| `config.yml`  | Render the full `/opt/AdGuardHome/AdGuardHome.yaml` from a Jinja template before the container starts; a change restarts the container once. |
| `cert.yml`    | The wildcard certificate via `roles/lego_cert` (first issuance + systemd renewal timer; the container restarted only when a renewal replaced the cert). |

## DNS chain context

```
clients (per VLAN) --> AdGuard Home :53 --> PROD OPNsense FW Unbound
                                        --> dnscrypt-proxy --> upstream resolver
```

AdGuard is the per-client policy layer; recursion/encryption happen on the FW.

## Key variables (`defaults/main.yml`)

| Variable | Default | Notes |
|----------|---------|-------|
| `adguard_ip` / `adguard_ip6` | `10.1.3.101` / `fd01:3::101` | VM addresses (used in internal rewrites). |
| `adguard_domain` | `platform_domain` | **Prod** wildcard (NOT the test subdomain). |
| `adguard_upstreams` | `["10.1.3.1"]` | See caveat below. |
| `adguard_renew_days` | `30` | Renew when cert expires within N days. |
| `adguard_cf_vault_path` | `{env}/cloudflare/{zone}` | Vault KV path of the zone secret (keys `api_token`, `acme_email`); read via the `vault_secret` role. |
| `adguard_admin_vault_path` | `{env}/adguard/admin` | Admin creds in Vault (generated once). |
| `adguard_vlan_clients` | 10 VLANs | Per-VLAN persistent clients; parental on `iot`+`cctv`, safe-search on `iot`. |

## Upstream caveat

The PROD OPNsense FW currently has **dnscrypt-proxy disabled** and Unbound
recursing on `:53`, so the default upstream is the SVC gateway `10.1.3.1`
(port 53). If Unbound is later moved to `:53530`, set:

```yaml
adguard_upstreams: ["10.1.3.1:53530"]
```

## Run

```bash
ansible-playbook playbooks/adguard-prod.yml -i inventories/prod/hosts.yml
```

Reaching the SVC VLAN from the controller requires the prod FW to permit
OOB → SVC forwarding (rune-routing); the inventory entry uses a `ProxyJump`
through `by-rune@10.6.239.196`.

## Assumptions

- `AdGuardHome.yaml` is rendered at `schema_version: 28` (current AdGuard Home).
- bcrypt generation uses the `bcrypt` Python module on the **controller**
  (rounds 10), matching the bash script.
