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

## Planned change of the primary (drills of 2026-10-04)

`playbooks/ha-drill.yml --tags redis`. One atomic step: writes are paused on the primary (`CLIENT PAUSE … WRITE`), `WAIT 1` confirms the replica has every write, the Sentinels fail over, the former primary is made a replica at once, the pause is released.

Why the pause: the endpoint follows a new primary only after six good checks (about 18 s — the margin that keeps a restarted old primary out of rotation until the Sentinels have demoted it). Without the pause the old primary stays writable during that time and those writes are discarded when it becomes a replica (first drill: promoted 12:35:39.9, endpoint on the new primary 12:35:58.0). A pause alone is not enough either: it also stops the Sentinels' hello on that member, so they fail over by themselves after `down-after` (5 s) and can only demote the paused member when the pause ends (second drill).

What clients see on a planned change: writes wait, then errors until the endpoint is on the new primary; nothing is lost. Third drill, with the atomic step: writes paused 15:21:54.9, replica promoted 15:21:56.1, former primary a replica 15:21:56.7, endpoint on the new primary 15:22:11.4 — 16.5 s. An unplanned failure (the primary is gone) has no such window: measured 21 s in the rehearsal.

## A member lost, and a member restarted (kill drills of 2026-10-04)

`playbooks/ha-drill.yml --tags redis-kill`: the primary's container is killed, the gap is read from the container's recorded end and the endpoint's log (new primary up **and** named by two Sentinels), the member is started again and must return as a replica without having received a session.

- **Gap for clients:** 7.6 s on 2026-10-05, 7.0 s on 2026-10-04 (9.7 s with the endpoint's first routing rule, 21 s before the tuning): the Sentinels need about 4.5 s (`down-after 3 s`, agreement, promotion), the endpoint about 2 s more (the new primary's own check, then two Sentinels naming it).
- **A restarted member claims to be a master** until the Sentinels make it a replica again (some seconds). The endpoint sends it nothing in that time: a member is used only while the Sentinels name it.
- **Its start file is static** (`include redis.conf`, root's): Redis cannot rewrite it. Until this drill a member that had been through a failover could not restart — the rewritten file declared every login a second time and loaded the image's bundled modules a second time. See `roles/redis/README.md`.
- **Planned change** (`--tags redis`) with the same endpoint rule: about 3 s of refused connections after the pause.
