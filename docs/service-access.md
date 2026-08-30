# Internal Service Access

How to reach the internal `*.by-research.be` services from a VPN client or an
out-of-band (OOB) admin desk. Every service lives behind **Traefik** on the
internal network (ingress **`10.1.2.110`**); your machine must resolve these
names to the ingress and be permitted through the three gates below.

> Source of truth: the OPNsense DNS catalog (`inventories/prod/group_vars/opnsense.yml`,
> split-horizon → Traefik). This doc is a human summary — regenerate the list from
> the catalog if services change.

## Hosts file

Windows: `C:\Windows\System32\drivers\etc\hosts` (edit in an **elevated Notepad** —
append scripts corrupt it). Linux/macOS: `/etc/hosts`. Save, then hard-refresh.

```text
# === by-research.be internal services -> Traefik (VPN/OOB access) ===
10.1.2.110 gitlab.by-research.be registry.by-research.be pages.by-research.be
10.1.2.110 jumpserver.by-research.be
10.1.2.110 authentik.by-research.be
10.1.2.110 vault.by-research.be vaultwarden.by-research.be
10.1.2.110 pgadmin.by-research.be netbox.by-research.be
10.1.2.110 nextcloud.by-research.be netbird.by-research.be
10.1.2.110 kroki.by-research.be plantuml.by-research.be drawio.by-research.be
10.1.2.110 seaweedfs.by-research.be s3.by-research.be
10.1.2.110 traefik.by-research.be
```

## Service map

17 Traefik-fronted services (SSO via Authentik).

| FQDN | Service | Purpose |
|---|---|---|
| `gitlab.by-research.be` | GitLab | Source, CI/CD, MRs |
| `registry.by-research.be` | Container Registry | GitLab image registry |
| `pages.by-research.be` | GitLab Pages | Static sites (wildcard `*.pages`) |
| `jumpserver.by-research.be` | JumpServer | Bastion — browser SSH/RDP to all hosts |
| `authentik.by-research.be` | Authentik | SSO / identity — needed for every login |
| `vault.by-research.be` | Vault | Secrets store |
| `vaultwarden.by-research.be` | Vaultwarden | Password manager |
| `pgadmin.by-research.be` | pgAdmin | PostgreSQL admin |
| `netbox.by-research.be` | NetBox | IPAM / DCIM |
| `nextcloud.by-research.be` | Nextcloud | Files |
| `netbird.by-research.be` | NetBird | VPN admin dashboard |
| `kroki.by-research.be` | Kroki | Diagram render (Graphviz, D2, …) |
| `plantuml.by-research.be` | PlantUML | UML render (standalone server) |
| `drawio.by-research.be` | draw.io | Diagram editor |
| `seaweedfs.by-research.be` | SeaweedFS | Object-store console |
| `s3.by-research.be` | S3 API | SeaweedFS S3 endpoint |
| `traefik.by-research.be` | Traefik | Ingress dashboard |

## The three gates (why a name might not load)

All three must pass; debug one at a time.

1. **Routing** — the desk must route the platform subnets via the firewall:
   `route -p add 10.1.0.0 mask 255.255.0.0 10.6.239.196` (elevated). Without it,
   packets never reach Traefik.
2. **DNS** — `*.by-research.be` must resolve to `10.1.2.110` (the hosts block
   above, or point the desk's DNS at the resolver — see Notes).
3. **Allowlist** — internal routes are IP-allowlisted at Traefik. A new admin
   desk IP gets **403 Forbidden** until it's added server-side
   (`inventories/prod/group_vars/all/traefik.yml` → `traefik_route_admin_cidrs`).

Diagnostic (bypasses DNS by IP):
`curl.exe -k -I --max-time 8 https://10.1.2.110 -H "Host: vault.by-research.be"` —
`200/307` = routing+allowlist OK (only DNS left); `timeout` = gate 1; `403` = gate 3.

## Notes

- **`mail.by-research.be` is PUBLIC** (WAN IP for external mail clients) — **not**
  Traefik-internal. Do **not** point it at `10.1.2.110`; that breaks webmail.
- **`*.pages.by-research.be` is a wildcard** — a hosts file can't wildcard; add
  each `<project>.pages.by-research.be` line as needed (the apex `pages.` is in
  the block).
- **Best fix (no upkeep):** point the desk's DNS at the internal resolver
  **`10.6.239.196`** → every `*.by-research.be` (wildcards included) resolves
  automatically. VPN clients get `10.1.4.x` inside `10.1.0.0/16`, so all three
  gates pass automatically — no hosts file needed at all.
