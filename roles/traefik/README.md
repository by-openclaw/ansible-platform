# role: traefik

Traefik v3 reverse-proxy / HTTPS ingress on a dedicated LXC (`lxc-traefik-01`,
DMZ `10.1.2.110` / `fd01:2::110`). The single front door for the platform
cluster's web UIs (Authentik, NetBox, …).

## What it does
- Installs the pinned Traefik binary (`v3.7.4`) + `lego` (Cloudflare DNS-01) +
  a systemd unit.
- Issues/renews a **wildcard `*.by-research.be`** cert via ACME **DNS-01
  (Cloudflare)** — reuses the `roles/adguard` lego flow. DNS-01 needs only
  outbound Cloudflare API, so certs work with no public inbound.
- Static config (`/etc/traefik/traefik.yml`): entrypoints `web :80` (→ redirect)
  and `websecure :443` (dual-stack bind), file provider, dashboard.
- Dynamic config (`/etc/traefik/dynamic/dynamic.yml`): TLS default cert + the
  dashboard router, restricted to internal networks (`ipAllowList`).
- Daily renewal cron (03:23) → reload Traefik.

## Run
```bash
ansible-playbook -i inventories/prod/hosts.yml playbooks/traefik.yml --check --diff   # dry-run
ansible-playbook -i inventories/prod/hosts.yml playbooks/traefik.yml                   # apply
```
Reaches the DMZ LXC via ProxyJump through the prod FW (`by-rune@10.6.239.196`),
login user **root** (LXC).

## Internal vs public
- **Internal (this role):** dual-stack on the LAN; valid HTTPS via the wildcard
  cert; dashboard at `https://traefik.by-research.be` (internal only).
- **Public (separate, WAN2 bring-up):** Telenet WAN2 static `.222` →
  `opn_dnat_rules` (IPv4 :80/:443 → `10.1.2.110`) **+** Telenet IPv6 **GUA**
  prefix → routed FW pass to a GUA on Traefik (no NAT66). ULA (`fd01:2::`)
  cannot be exposed publicly. Tracked with infra #21 / ansible #32.

## Adding backends
Append routers/services to `dynamic.yml.j2` as each cluster service comes up
(example shape is in the template comments) + add an Unbound host-override for
its `*.by-research.be` name (split-horizon local).

## Follow-ups
- Harden Traefik to a dedicated non-root user (+ `CAP_NET_BIND_SERVICE`, cert
  group-read) — runs as root today for cert access on the isolated LXC.
