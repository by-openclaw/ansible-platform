# role: redis (Docker)

One member of the shared **Redis pair** (services/0004): a primary and a replica; three
Sentinels (`roles/redis_sentinel`) decide which member is the primary. Internal-only — a TCP
service, **not** behind Traefik. Consumers connect to the data endpoint (`roles/dbproxy`),
which routes to the member that reports itself master.

Run: `ansible-playbook playbooks/redis.yml` (members one at a time, then the Sentinels).

- **Container** (through `roles/service_scaffold`): pinned `redis_image`, started as the redis
  uid, **read-only root filesystem**, no capability; data on the `redis-data` volume (AOF).
  Published on the member's service address + loopback, TLS only (`port 0`, `tls-port 6379`).
- **Two files**:
  - `redis.conf` (Ansible's, read-only in the container): TLS, authentication, persistence,
    replication settings, the consumer logins.
  - the **start file** (`redis_runtime_file`): one `include` of `redis.conf` plus, on a
    replica, its `replicaof` line. Redis rewrites this file itself when Sentinel changes its
    role, so a restart keeps the role. The role normalises it on every run from the member's
    LIVE role — a rewrite copies every setting into it, and a copy left there would silently
    override a later change of `redis.conf`.
- **Logins**: the `default` user (`requirepass`, Vault `redis/admin`) is the administration,
  replication and Sentinel login. Every consumer has its own (`platform_redis_users`, Vault
  `redis/users/<name>`): everything except administration commands; the endpoint's check login
  may only run `INFO` and `PING`. ACLs do not replicate — both members render the same list.
- **Replication**: `masterauth`, `replica-announce-ip` = the member's FQDN (the container's
  own address means nothing outside its host), TLS (`tls-replication yes`).
- **TLS**: the shared wildcard certificate (`roles/tls_cert`), owned by the redis uid.

## Operating it

| Need | How |
|---|---|
| Who is primary | `docker exec redis-sentinel redis-cli --tls … -p 26379 sentinel master platform-redis` |
| Planned primary change | `… sentinel failover platform-redis` |
| A member's role | `docker exec redis redis-cli --tls … info replication` |

Never run `REPLICAOF` by hand while the Sentinels are up: they own the roles of the members.

## Limits

- Two members: the pair survives the loss or the maintenance of one. Replication is
  asynchronous — a failover can lose the last writes (caches, sessions, queues: acceptable for
  what the platform stores there).
- Database numbers are not an access boundary: an ACL cannot restrict a login to a database
  number. The logins give attribution, revocation and no administration commands.
