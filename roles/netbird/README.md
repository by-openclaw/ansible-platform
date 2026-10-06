# role: netbird

NetBird CE (self-hosted zero-trust VPN) on the `netbird` inventory group, deployed in
the **official multi-container model** — a pure-Ansible reproduction of what NetBird's
`getting-started.sh` (`configure.sh` + the official `management.json.tmpl` /
`docker-compose.yml.tmpl.traefik`) generates for an **existing Traefik** with
**Authentik as the direct OIDC login** (the model the goauthentik.io NetBird guide
targets). The `.sh` never runs. Catalog row `name: netbird` in
`inventories/prod/group_vars/all/services.yml`; service page `docs/services/netbird.md`.

## What it does

- Five pinned containers (`defaults/main.yml`, never `:latest`), run through
  `roles/service_scaffold` (containers step): **dashboard** (SPA, PKCE login straight
  to Authentik), **management** (control plane + REST/gRPC API on `:33073`, validates
  Authentik JWTs, syncs users through the IdP-manager service account), **signal**
  (gRPC h2c `:10000`, ws-proxy `:8081`), **relay** (`:33080`, exposed as
  `rels://<vpn fqdn>:443/relay`), **coturn** (host network, STUN/TURN `:3478`, runs as
  `nobody`). Each server also serves Prometheus `/metrics`, published on
  `netbird_*_metrics_port` for the monitoring host (catalog `metrics_ports`).
- **Stores on the shared PostgreSQL** (`roles/postgres_db`: `netbird` + `netbird_events`,
  own users, `sslmode=verify-full` against the platform CA). The one-time SQLite →
  PostgreSQL migration (2026-09) is archived in `tasks/_archive/store_migration.yml`;
  `tasks/store.yml` refuses a store that is still on SQLite and points there.
- **`management.json`** is rendered from the official template; the OIDC endpoints come
  from Authentik's live `.well-known/openid-configuration` (`tasks/oidc-discovery.yml`),
  never hardcoded. Authentik is pinned to Traefik in `/etc/hosts` (internal resolve).
- **Traefik** (file provider, `roles/traefik_route`, `tasks/route.yml`): six routers on one
  host name — gRPC h2c (`/management.ManagementService/`, `/signalexchange.SignalExchange/`),
  `/api` + `/ws-proxy/management`, `/ws-proxy/signal`, `/relay`, dashboard catch-all.
  Public and un-gated on purpose: remote peers hold long-lived gRPC streams.
- **Phase 2 (machine-only):** `tasks/automation-token.yml` mints a client-credentials JWT
  as the Authentik service account `svc-netbird-{env}`, gets-or-creates the NetBird
  **service user** of the same name and keeps its token in Vault (reused while valid;
  `tasks/enforce-no-human-pat.yml` revokes any token on a non-service user). With it:
  `tasks/routing-peer.yml` (this host as routing peer: routers group, reusable setup key
  in Vault, internal-LAN route, AdGuard nameserver, pinned apt client, WireGuard port +
  external IP map), `tasks/vpn-tiers.yml` (web `/32` routes on `All`, the LAN route on
  `vpn-full`, admin-group members → NetBird role `admin` + `vpn-full`),
  `tasks/account-settings.yml` (peer login expiration, no redundant user approval).
- `roles/host_firewall` rules for the native listeners; `tasks/retired.yml` removes what
  the role no longer manages (old notifier, secret copies superseded by Vault, SQLite
  files and the `store-backup-*` copy once PostgreSQL is proven).

## Auth model

No local owner, no break-glass IdP. `single-account-mode` keeps every `@<domain>`
user in one NetBird org; the account owner is the identity that logged in first (here
the service account, through the IdP-manager login). Access is IdP-enforced: only
members of the service's access group may authenticate (`group_vars/all/sso.yml`,
`restrict_to_group`); members of the admin group are NetBird admins (people.yml →
`platform_service_groups.netbird.admin`).

| Flow | Used by | Authentik endpoint |
|---|---|---|
| PKCE | dashboard browser login | `authorization` / `token` |
| Device | CLI / mobile `netbird up` | `device_authorization` |
| Client credentials | IdP-manager user sync + phase-2 bootstrap | `token` (service account) |

## Secrets (Vault only)

`secret/{env}/netbird/core` (datastore key, relay secret, TURN password — get-or-create),
`oidc` (minted by `roles/authentik`), `authentik-sa`, `db-pgsql` + `db-pgsql-events`
(minted by `postgres_db`), `automation` (service-user token), `router-setup-key`.

## Run

```bash
ansible-playbook playbooks/netbird.yml --check --diff   # dry-run (read-only probes still run)
ansible-playbook playbooks/netbird.yml                  # apply; second run changed=0
```

A pin bump recreates the affected container (peers keep their tunnels; management
restarts in seconds). Removal: `playbooks/decommission-service.yml` (catalog
`state: absent`).

## Public exposure (FW catalog, `ansible-opnsense`)

`443/TCP` rides the WAN → Traefik DNAT; `3478/UDP+TCP` (STUN/TURN), the TURN relay
range and `51820/UDP` (routing-peer WireGuard) are DNATed to the NetBird host through
the `host4_netbird`/`host6_netbird`, `port_stun`, `port_netbird_wg` aliases.
