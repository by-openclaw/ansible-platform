# Redis (shared instance) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: redis`). Role `roles/redis`, play `playbooks/redis.yml`, guests `lxc-redis-01` and `lxc-redis-02` (a primary and a replica) with three Sentinels (`roles/redis_sentinel`: the two members and the endpoint guest); consumers connect to the data endpoint ([dbproxy](dbproxy.md)). Database allocation: `inventories/prod/group_vars/all/redis.yml` (`platform_redis_databases`). Audit: [`docs/audits/redis-2026-10-03.md`](../audits/redis-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — no user interface (`sso: none`); clients authenticate with the instance password over TLS (TLS-only listener, the plain port is closed).
2. **Authentik application:** none.
3. **Access model:** one login per consumer (`platform_redis_users`: NetBox, Nextcloud, GitLab — everything except administration commands) and a check login for the endpoint (`INFO`, `PING` only); the `default` user is the administration, replication and Sentinel login. Database numbers separate the consumers' keys (`platform_redis_databases`; an ACL cannot restrict a login to a database number). Authentik is not a consumer any more (2025.10+ keeps its state in PostgreSQL). Until a consumer's own change moves it, it still connects to the first member as the `default` user. No command is renamed; `protected-mode` is on.
4. **Vault paths:** `secret/{env}/redis/admin` (the `default` user), `secret/{env}/redis/users/<name>` (one per consumer login and the check login), `secret/{env}/redis/sentinel` (the Sentinels' own password).
5. **Ansible adapter + vars:** `roles/redis` (`defaults/main.yml`: pin `redis_image`, TLS (the platform wildcard), persistence (AOF + RDB), memory policy, members; `templates/redis.conf.j2` settings, replication and logins; `tasks/config.yml` renders `redis.conf` and the start file (`include` + the member's `replicaof`, normalised from its live role), restarts the member when the file is newer than the process; `tasks/container.yml` the container through the scaffold (redis uid, read-only root filesystem, no capability); `tasks/absent.yml` one member's teardown); `roles/redis_sentinel` (three Sentinels: the two members and the endpoint guest); the endpoint's Redis route in `roles/dbproxy`.
6. **Removal notes:** not removable while consumers exist; class E for the caches, B for NetBox's queues — the data volume (`redis-data`, AOF) in the PBS guest image. One member: `-e redis_state=absent -e redis_absent_confirm=<member>`, then the play rebuilds it from the primary.

## Notifications (services/0005)

1. **Transport:** none — Redis sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus `node` + `cadvisor` on both members, the endpoint's `haproxy_backend_active_servers` → `RedisEndpointNoPrimary` → Alertmanager → Discord/mail.
4. **Logs:** the container on journald → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class E/B (`docs/backup.md`): caches rebuild; the append-only file and RDB snapshots under the `redis-data` volume are in the PBS guest image (daily). Restore = play + the volume from PBS (or an empty instance: consumers repopulate their caches; NetBox re-queues).
