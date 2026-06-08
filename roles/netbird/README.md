# role: netbird

NetBird CE (self-hosted Zero-Trust VPN) on `lxc-netbird-01` (SVC `10.1.3.181`),
deployed in the **official combined model** — a pure-Ansible reproduction of what
`getting-started.sh` generates for the "existing Traefik" path (we never run the
`.sh`). Replaces the retired defguard.

## What it does
- Two pinned containers (never `:latest`):
  - **`netbird-server`** (`netbirdio/netbird-server:0.72.2`) — one image bundling
    Management + Signal + Relay + STUN + the **embedded Dex IdP**. Reads
    `config.yaml`; listens `:80` (HTTP REST + gRPC h2c + WebSocket) and `:3478/udp`
    (STUN). Store = **sqlite** in the `netbird_data` volume (official default).
  - **`netbird-dashboard`** (`netbirdio/dashboard:v2.39.0`) — web UI; authenticates
    against the embedded Dex (`/oauth2`).
- Fronted by **our Traefik** via the file provider (`netbird.yml` dropped on the
  Traefik host): gRPC routers → **h2c**, backend (`/api`,`/oauth2`,`/relay`,
  `/ws-proxy/`) → server, catch-all → dashboard. (Translation of the official
  docker labels — same routes, file provider instead of the docker provider.)
- **Bootstrap (Ansible, headless):** `POST /api/setup` creates the first owner
  (`adm_yboujraf`, a local Dex break-glass account) + a PAT; then
  `POST /api/identity-providers` adds **Authentik** as an external OIDC IdP (Dex
  federates to it). Both idempotent.

## Auth model
Dex is always-on (embedded) and is the bootstrap/break-glass IdP — like `akadmin`
for Authentik or the local `admin` for Nextcloud. **Authentik is the SSO** everyone
logs in with (an extra login button; Dex federates upstream). The Authentik OAuth2
provider is provisioned by `roles/authentik` (slug `netbird`, regex redirect
covering `/oauth2/callback/<id>`).

## Run
```bash
ansible-playbook -i inventories/prod/hosts.yml playbooks/netbird.yml --check --diff   # dry-run
ansible-playbook -i inventories/prod/hosts.yml playbooks/netbird.yml                   # apply
```
Reaches the SVC LXC via ProxyJump through the prod FW (`by-rune@10.6.239.196`),
login user **root**.

## Public exposure (FW)
- `443/TCP` (dashboard + API + gRPC + relay/WS) rides the **existing** Telenet
  WAN→Traefik DNAT.
- `3478/UDP` (STUN) needs its **own** WAN DNAT → `10.1.3.181` (added to the OPNsense
  catalog, lib-first via `FwDnatManager`). No separate relay UDP range (relay is
  multiplexed over 443 WebSocket in the combined model).

## Switch to Postgres (optional)
Set `netbird_store_engine: postgres` and add `store.dsn` (libpq) in `config.yaml.j2`
— the rest is unchanged.
