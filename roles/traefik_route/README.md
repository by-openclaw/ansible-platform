# role: traefik_route

Reusable per-service helper: registers a service **router** on the Traefik host
by dropping a watched dynamic-config file into Traefik's file-provider directory
(`/etc/traefik/dynamic/<name>.yml`, delegated to the Traefik host). Traefik's
file provider watches the directory, so no reload is needed.

Implements step 1 of the per-service pattern (Traefik router + wildcard TLS).
Every web service (pgAdmin, Authentik, NetBox, …) includes it:

```yaml
- name: "route | Publish <svc> via Traefik"
  ansible.builtin.include_role:
    name: traefik_route
  vars:
    traefik_route_name: pgadmin
    traefik_route_fqdn: "pgadmin.by-research.be"
    traefik_route_backend_url: "http://10.1.3.140:8080"
    traefik_route_internal_only: true   # ipAllowList; false for public svc
```

| var | default | purpose |
|---|---|---|
| `traefik_route_host` | `lxc-traefik-01` | Traefik host (delegate target) |
| `traefik_route_dynamic_dir` | `/etc/traefik/dynamic` | file-provider dir |
| `traefik_route_internal_only` | `true` | add ipAllowList middleware |
| `traefik_route_internal_cidrs` | internal ranges | allowed sources |
