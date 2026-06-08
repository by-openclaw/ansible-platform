<!--
Copyright (c) BY-SYSTEMS SRL
SPDX-License-Identifier: Apache-2.0
https://github.com/by-openclaw/ansible-platform
-->
# Role: `netbird`

NetBird CE — self-hosted Zero-Trust VPN on `lxc-netbird-01` (SVC `10.1.3.181`).
**Replaces defguard**, whose external OIDC SSO is license-gated in 2.0.1; NetBird
CE does external OIDC SSO for free (self-hosted, no netbird.io account).

## Containers (pinned tags, never `:latest`)

| Container | Image | Port (on `.181`) | Purpose |
|---|---|---|---|
| management | `netbirdio/management:0.72.2` | 33073 (h2c) | control plane + REST/gRPC API + `management.json` |
| signal | `netbirdio/signal:0.72.2` | 10000 (h2c) | peer ICE candidate exchange |
| relay | `netbirdio/relay:0.72.2` | 33080 | TURN-like WS fallback |
| dashboard | `netbirdio/dashboard:v2.39.0` | 8088 → :80 | web UI |
| coturn | `coturn/coturn:4.6.2` | 3478/udp (host net) | STUN/TURN |

- **Store:** shared cluster PostgreSQL (`postgres_db: netbird`), verify-full TLS.
- **IdP:** Authentik — dashboard **PKCE** login + CLI **device-code** flow. IdP
  user-management is left off (cloud-gated); users are JIT-created on first login.
- **Ingress:** Traefik file provider, multi-router with **h2c** for the gRPC
  backends (`roles/netbird/templates/traefik-netbird.yml.j2`). Public (no
  ipAllowList) — remote peers need it.

## Deploy

```bash
# 1. infra-terraform-proxmox#46 applied (lxc-netbird-01 exists)
# 2. Authentik provider blueprint for netbird applied (follow-up PR)
# 3. dual-WAN FW DNAT: 443/TCP + 3478/UDP + 49152-65535/UDP on Telenet + Proximus
ansible-playbook -i inventories/prod/hosts.yml playbooks/netbird.yml
```

## ⚠️ Live-verify after first deploy (authored against the upstream templates)

OIDC self-hosted configs almost always need one live tune. After deploy, verify:
1. `https://netbird.by-research.be` loads and **redirects to Authentik**, login works.
2. `netbird login` (CLI) completes the **device-code** flow.
3. A peer connects (P2P or via relay/coturn) — check `management` logs for token
   validation (`AuthKeysLocation` / `AuthUserIDClaim=sub`) and coturn relaying.
4. If login 401s: check the dashboard `NETBIRD_TOKEN_SOURCE` (accessToken vs
   idToken) and `management.json` `AuthAudience` == the Authentik client_id.

## Follow-ups (separate PRs)
- Authentik `authentik_oidc_apps: netbird` blueprint (device_code grant + redirect
  URIs `https://netbird.by-research.be/auth`, `/silent-auth`, `http://localhost:53000`).
- dual-WAN FW ingress (OPNsense catalog) + split-horizon DNS.
- decommission defguard.
