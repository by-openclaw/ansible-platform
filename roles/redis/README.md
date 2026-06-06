# role: redis (Docker)

Shared **Redis** as a Docker container on `lxc-redis-01` (SVC `10.1.3.117`).
Internal-only — a TCP service, **not** behind Traefik. Cache / broker for
Authentik + NetBox.

All-Docker pivot: **upgrade = bump `redis_image` tag** → ansible pulls + recreates
the container; data persists in the `redis-data` named volume (`/data`). Maps
cleanly to a future k8s Deployment/PVC.

- Pinned `redis:8` image; depends on `base` + `docker` (nested LXC).
- Retires any prior **native** install first (`migrate.yml` stops/masks
  `redis-server`) so the container can bind `:6379`.
- Published only on `10.1.3.117:6379` + `127.0.0.1:6379`.
- **TLS (`rediss://`):** the shared wildcard `*.by-research.be` cert is
  distributed by the `tls_cert` role (owned by the container's redis uid 999) and
  mounted read-only. Plaintext disabled (`port 0`), `tls-port 6379`,
  `tls-replication yes`.
- **Auth:** `requirepass` generated once and stored in the controller secret
  store (`db-redis.json`, `0600`, `no_log`).
- **Durable + HA-adoptable:** `appendonly` (AOF) → a future replica / Sentinel
  can attach with no rebuild and no data loss.

Config is a mounted `redis.conf` (`/etc/redis/conf/redis.conf`). Clients connect
over TLS with the password, e.g.
`rediss://:<pw>@lxc-redis-01.by-research.be:6379/0`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/redis.yml`
(reaches the SVC LXC via OPNsense ProxyJump, login `root`).
