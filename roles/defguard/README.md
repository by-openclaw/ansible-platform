# role: defguard (Docker)

**Defguard** — WireGuard VPN + **Authentik OIDC SSO** + **tunnel MFA** — on
`lxc-defguard-01` (SVC `10.1.3.180`). Three containers from pinned images:
`defguard-core` (control plane + web/enrollment UI, `ghcr.io/defguard/defguard`),
`defguard-proxy` (enrollment / desktop-client proxy,
`ghcr.io/defguard/defguard-proxy`) and `defguard-gateway` (WireGuard data plane,
derived from `ghcr.io/defguard/gateway`). Upgrade = bump the `defguard_*_image`
tags.

- depends `base` + `docker`. Includes `postgres_db` to create its own DB+role.
- **Postgres** over `PGSSLMODE=verify-full` (`PGSSLROOTCERT` = mounted host CA
  bundle) — shared cluster svc. **No Redis** (defguard core does not require it).
- **Userspace WireGuard (critical):** this LXC is unprivileged + nesting, so the
  gateway CANNOT use the host kernel WireGuard module (same failure class as
  keyctl). The gateway runs in userspace (`DEFGUARD_USERSPACE=1`) using
  **wireguard-go**, which is NOT shipped in the stock gateway image — the role
  builds a derived image (`Dockerfile.gateway-userspace.j2`, bundling
  wireguard-go) and runs it with `cap_add: NET_ADMIN` + `devices: /dev/net/tun`.
- Secrets (`DEFGUARD_SECRET_KEY`, `DEFGUARD_AUTH_SECRET`,
  `DEFGUARD_GATEWAY_SECRET`, `DEFGUARD_YUBIBRIDGE_SECRET`, break-glass admin
  password) generated once and stored in the controller secret store
  (`defguard-core.json`, `no_log`). DB password loaded from its own secret file.
- **Authentik OIDC:** the role is built SSO-ready — it consumes the OIDC client
  id/secret from `defguard-oidc.json` (`DEFGUARD_OPENID_*`) when present and
  `defguard_oidc_enabled` is true. Creating the Authentik OIDC application is a
  SEPARATE SSO phase (see PR description / follow-ups).
- Host CA store mounted into every container.
- **Internal-only:** web/enrollment UI published via `traefik_route`
  (`defguard.by-research.be`, wildcard TLS + `ipAllowList`).
- **WireGuard ingress:** WAN udp/51820 (alias `port_wg`, infra/0004 §8) is
  port-forwarded to this LXC's gateway in the OPNsense catalog. The WG client
  pool reuses the dedicated VPN zone `net4_vpn` (`10.1.4.0/24`).

## Host prerequisite — /dev/net/tun (userspace WireGuard)

Userspace wireguard-go needs the `/dev/net/tun` device node. This LXC is
**unprivileged**, so the node is NOT present by default and `mknod` inside the
guest is denied by the device cgroup — even though the PVE host kernel has the
`tun` module loaded (`/sys/class/misc/tun/dev` = `10:200`). The host must grant
the device once. On the PVE node, add to `/etc/pve/lxc/550.conf`:

```
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file 0 0
```

then `pct reboot 550`. The role **detects** `/dev/net/tun`: if absent, it brings
up core + proxy + UI and skips the gateway (printing the exact host config above)
rather than enabling a host kernel hack from inside the guest. Once the node
exists, re-run the playbook to start the gateway. **This host change requires
operator authorization (no rune key on the PVE host today).**

Initial admin = local **break-glass** `admin` / `defguard_admin_email`; password
in `defguard-core.json`. SSO via Authentik (OIDC) is wired once the Authentik app
+ `defguard-oidc.json` exist. Health: `/api/v1/health` (200) on `:8000`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/defguard.yml --vault-password-file .vault_pass`.
Requires the FW DMZ→SVC `:8000` rule + Unbound override (opnsense catalog).
