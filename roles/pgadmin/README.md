# role: pgadmin

pgAdmin 4 (Docker) on `lxc-pgadmin-01` (SVC `10.1.3.140`) — PostgreSQL admin UI.

- Runs the pinned `dpage/pgadmin4` image (no `:latest`) via `community.docker`;
  depends on `base` + `docker` (nested LXC).
- Container bound to the SVC IP `10.1.3.140:8080` so Traefik (on the DMZ host)
  can reach it; persistent named volume `pgadmin-data`.
- Admin login generated once + stored in the controller secret store
  (`pgadmin-admin.json`, `0600`, `no_log`).
- **Internal-only:** published via the `traefik_route` role
  (`pgadmin.by-research.be` → backend), wildcard TLS + `ipAllowList` — **no**
  public Cloudflare record, **no** second proxy (Traefik only).
- `PGADMIN_CONFIG_PROXY_X_*` set so pgAdmin honours Traefik's `X-Forwarded-*`.

Connects to Postgres over TLS (`sslmode=verify-full`, publicly-trusted LE CA).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/pgadmin.yml`
(reaches the SVC LXC via OPNsense ProxyJump, login `root`).
