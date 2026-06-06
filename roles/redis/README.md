# role: redis

Shared **Redis** on `lxc-redis-01` (SVC `10.1.3.117`). Internal-only — a TCP
service, **not** behind Traefik. Cache / broker for Authentik + NetBox.

- Installs `redis-server` (Debian trixie, Redis 8); depends on `base`.
- **TLS (`rediss://`):** the shared wildcard `*.by-research.be` cert is
  distributed by the `tls_cert` role (issued once on `lxc-traefik-01`, **not**
  re-issued here). Plaintext disabled (`port 0`), `tls-port 6379`,
  `tls-replication yes`.
- **Auth:** `requirepass` generated once and stored in the controller secret
  store (`db-redis.json`, `0600`, `no_log`).
- Binds loopback + the SVC addresses; `protected-mode`.
- **Durable + HA-adoptable:** `appendonly` (AOF) → a future replica / Sentinel
  can attach with no rebuild and no data loss.

Config is a drop-in (`/etc/redis/redis.conf.d/10-cluster.conf`) included as the
last line of `redis.conf`, so it overrides the Debian defaults.

Clients connect over TLS with the password, e.g.
`rediss://:<pw>@lxc-redis-01.by-research.be:6379/0`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/redis.yml`
(reaches the SVC LXC via OPNsense ProxyJump, login `root`).
