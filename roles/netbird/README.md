# role: netbird

NetBird CE (self-hosted Zero-Trust VPN) on `lxc-netbird-01` (SVC `10.1.3.181`),
deployed in the **official multi-container model** — a pure-Ansible reproduction
of what NetBird's `getting-started.sh` (`configure.sh` + the official
`management.json.tmpl` / `docker-compose.yml.tmpl.traefik`) generates for an
**existing Traefik** with **Authentik as the direct OIDC login** (the model the
[goauthentik.io NetBird guide](https://integrations.goauthentik.io/networking/netbird/)
targets). We never run the `.sh`. Replaces the retired combined/Dex deployment.

## What it does
- Five pinned containers (never `:latest`):
  - **`netbird-dashboard`** (`netbirdio/dashboard:v2.39.0`) — web UI/SPA. Sends the
    browser **straight to Authentik** to log in (PKCE). No Dex, no `/oauth2`.
  - **`netbird-management`** (`netbirdio/management:0.72.3`) — control plane + REST/
    gRPC API on `:33073`. Validates Authentik JWTs (`AuthKeysLocation` = Authentik
    JWKS) and **syncs the user list from Authentik** via the IdP-manager service
    account. Reads `management.json`. Store = **sqlite**.
  - **`netbird-signal`** (`netbirdio/signal:0.72.3`) — peer signalling: gRPC (h2c)
    on `:10000`, ws-proxy on `:80` (host `:8081`).
  - **`netbird-relay`** (`netbirdio/relay:0.72.3`) — relayed data path (`wss`) on
    `:33080`; exposed as `rels://vpn.by-research.be:443/relay`.
  - **`netbird-coturn`** (`coturn/coturn:4.6.2`, host network) — STUN/TURN on
    `:3478` (direct-connection optimisation; toggle `netbird_coturn_enabled`).
- **`management.json`** is rendered from the official template with our values; the
  five OIDC endpoints (issuer / jwks / token / device / authorization) are **not
  hardcoded** — `tasks/oidc-discovery.yml` fetches Authentik's live
  `.well-known/openid-configuration` and derives them (exactly like `configure.sh`).
- Fronted by **our Traefik** via the file provider (`netbird.yml` on the Traefik
  host), translating the official docker labels to split backends: gRPC routers →
  **h2c** (`/management.ManagementService/`, `/signalexchange.SignalExchange/`),
  REST/ws → management, `/relay` → relay, catch-all → dashboard. **No `/oauth2`.**
- Authentik is reachable from management internally: the management container gets
  an `extra_hosts` pin `authentik.by-research.be → Traefik`, so JWKS/token/device
  calls never hairpin out and survive the NetBird client rewriting `resolv.conf`.

## Auth model
There is **no local owner / break-glass IdP**. The **first `@by-research.be` user
to log in via Authentik becomes the account owner**, and `single-account-mode`
(`--single-account-mode-domain=by-research.be`) keeps every `@by-research.be` user
in **one** NetBird org (this is what fixes the per-user tenant forking the old
combined/Dex model produced). Three OIDC flows, all → Authentik:

| Flow | Used by | Authentik endpoint |
|---|---|---|
| PKCE | dashboard browser login | `authorization` / `token` |
| Device | CLI / mobile `netbird up` | `device_authorization` |
| IdP-manager | management user sync | service account `NetBird` (app token) |

The Authentik OAuth2 provider (`slug netbird`, **public** client, redirect regex
`https://vpn.by-research.be/.*` + `http://localhost:53000`) and the device-code
flow on the brand are provisioned on the Authentik side.

## Two-phase run
**Phase 1 — stack + login** (no PAT needed):
```bash
ansible-playbook -i inventories/prod/hosts.yml playbooks/netbird.yml --check --diff   # dry-run
ansible-playbook -i inventories/prod/hosts.yml playbooks/netbird.yml                   # apply
```
Then log in once at `https://vpn.by-research.be` (the owner is created).

**Phase 2 — routing peer + VPN tiers** (needs a NetBird PAT): in the dashboard
(Settings → personal access tokens) create a token, write it to
`netbird-setup.json` as `fields.personal_access_token`, and re-run the playbook.
This enrolls this host as a routing peer (advertises `10.1.0.0/16` + AdGuard DNS)
and sets the access tiers (web baseline on `All`, full on `vpn-full`).

Reaches the SVC LXC via ProxyJump through the prod FW (`by-rune@10.6.239.196`),
login user **root**.

## Public exposure (FW)
- `443/TCP` (dashboard + API + gRPC + relay/WS) rides the **existing** Telenet
  WAN→Traefik DNAT.
- `3478/UDP` (STUN/TURN) needs its own WAN DNAT → `10.1.3.181` (OPNsense catalog,
  lib-first via `FwDnatManager`).
