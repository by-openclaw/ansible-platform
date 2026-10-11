> **Archived 2026-10-11.** Superseded by [`docs/access.md`](../access.md), generated from the inventory
> (`playbooks/register.yml`). Kept for its notes on routing and name resolution from an administrator's
> desk; real names and addresses were replaced by placeholders (the repository is public — the values
> are in the inventory).

# Internal Service Access

How to reach the internal `*.<domain>` services from a VPN client or an
out-of-band (OOB) admin desk. Every service lives behind **Traefik** on the
internal network (ingress **`<address>`**); your machine must resolve these
names to the ingress and be permitted through the three gates below.

> Source of truth: the OPNsense DNS catalog (`inventories/prod/group_vars/opnsense.yml`,
> split-horizon → Traefik). This doc is a human summary — regenerate the list from
> the catalog if services change.

## Hosts file

Windows: `C:\Windows\System32\drivers\etc\hosts` (edit in an **elevated Notepad** —
append scripts corrupt it). Linux/macOS: `/etc/hosts`. Save, then hard-refresh.

```text
# === <domain> internal services -> Traefik (VPN/OOB access) ===
<address> gitlab.<domain> registry.<domain> pages.<domain>
<address> jumpserver.<domain>
<address> authentik.<domain>
<address> vault.<domain> vaultwarden.<domain>
<address> pgadmin.<domain> netbox.<domain>
<address> nextcloud.<domain> netbird.<domain>
<address> kroki.<domain> plantuml.<domain> drawio.<domain>
<address> seaweedfs.<domain> s3.<domain>
<address> traefik.<domain>
```

## Service map

17 Traefik-fronted services (SSO via Authentik).

| FQDN | Service | Purpose |
|---|---|---|
| `gitlab.<domain>` | GitLab | Source, CI/CD, MRs |
| `registry.<domain>` | Container Registry | GitLab image registry |
| `pages.<domain>` | GitLab Pages | Static sites (wildcard `*.pages`) |
| `jumpserver.<domain>` | JumpServer | Bastion — browser SSH/RDP to all hosts |
| `authentik.<domain>` | Authentik | SSO / identity — needed for every login |
| `vault.<domain>` | Vault | Secrets store |
| `vaultwarden.<domain>` | Vaultwarden | Password manager |
| `pgadmin.<domain>` | pgAdmin | PostgreSQL admin |
| `netbox.<domain>` | NetBox | IPAM / DCIM |
| `nextcloud.<domain>` | Nextcloud | Files |
| `netbird.<domain>` | NetBird | VPN admin dashboard |
| `kroki.<domain>` | Kroki | Diagram render (Graphviz, D2, …) |
| `plantuml.<domain>` | PlantUML | UML render (standalone server) |
| `drawio.<domain>` | draw.io | Diagram editor |
| `seaweedfs.<domain>` | SeaweedFS | Object-store console |
| `s3.<domain>` | S3 API | SeaweedFS S3 endpoint |
| `traefik.<domain>` | Traefik | Ingress dashboard |

## The three gates (why a name might not load)

All three must pass; debug one at a time.

1. **Routing** — the desk must route the platform subnets via the firewall:
   `route -p add <address> mask <mask> <address>` (elevated). Without it,
   packets never reach Traefik.
2. **DNS** — `*.<domain>` must resolve to `<address>` (the hosts block
   above, or point the desk's DNS at the resolver — see Notes).
3. **Allowlist** — internal routes are IP-allowlisted at Traefik. A new admin
   desk IP gets **403 Forbidden** until it's added server-side
   (`inventories/prod/group_vars/all/traefik.yml` → `traefik_route_admin_cidrs`).

Diagnostic (bypasses DNS by IP):
`curl.exe -k -I --max-time 8 https://<address> -H "Host: vault.<domain>"` —
`200/307` = routing+allowlist OK (only DNS left); `timeout` = gate 1; `403` = gate 3.

## Notes

- **`mail.<domain>` is PUBLIC** (WAN IP for external mail clients) — **not**
  Traefik-internal. Do **not** point it at `<address>`; that breaks webmail.
- **`*.pages.<domain>` is a wildcard** — a hosts file can't wildcard; add
  each `<project>.pages.<domain>` line as needed (the apex `pages.` is in
  the block).
- **Best fix (no upkeep):** point the desk's DNS at the internal resolver
  **`<address>`** → every `*.<domain>` (wildcards included) resolves
  automatically. VPN clients get `10.1.4.x` inside `<address>/16`, so all three
  gates pass automatically — no hosts file needed at all.
