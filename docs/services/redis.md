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

## Planned change of the primary

`playbooks/ha-drill.yml --tags redis`: one failover order to the Sentinels (`SENTINEL FAILOVER`). They promote the replica and make the former primary follow it; the endpoint uses a member only while it says master **and** two Sentinels name it, so it moves with them.

- **What clients see** (measured 2026-10-05 22:10 UTC): the Sentinels switched in 1.1 s (order 22:10:27.4, done 22:10:28.5). The endpoint used the new primary's answers from 22:10:28.97, when two Sentinels named it, but for 5.4 s more it still counted the former primary as named too and — two candidates — refused connections until 22:10:34.4. Then it served from the new primary. The former primary kept claiming to be a master until 22:10:44; the endpoint no longer used it.
- **To shorten:** those 5.4 s are the time the endpoint takes to drop a member the Sentinels no longer name (its `fall` on that check). Lowering it is a tuning of `roles/dbproxy`, to be measured by this drill.
- **What can be lost:** a write the former primary accepted between the order and the moment the endpoint stopped using it alone (about 1.5 s in that run) and had not yet replicated. There is no write pause before the order.
- **Why no pause any more.** Until 2026-10-05 the change paused writes on the primary first (`CLIENT PAUSE … WRITE`), so that nothing could be lost. A pause also holds the Sentinels' own messages to the primary: after `down-after` (3 s) they declare it down and start a failover of their own. As one script the whole change took about a second and stayed under that limit; as separate Ansible tasks, seconds apart, it did not — on 2026-10-05 the primary changed three times in 21 s (02 → 01 → 02 → 01) and clients were disturbed for about 40 s.
- **The zero-loss alternative** is to stop the primary's container cleanly: Redis hands its last writes to the replica before it exits, and the Sentinels then fail over as for a lost member (the gap of the next section, nothing lost).
- **Two minutes after any failover**, the Sentinels will not start another one for the same primary (twice `failover-timeout`, 60 s): a second failure in that window waits for it. Measured 2026-10-05: a primary killed 2 minutes after the flapping above was replaced only after 126 s.

## A member lost, and a member restarted (kill drills of 2026-10-04)

`playbooks/ha-drill.yml --tags redis-kill`: the primary's container is killed, the gap is read from the container's recorded end and the endpoint's log (new primary up **and** named by two Sentinels), the member is started again and must return as a replica without having received a session.

- **Gap for clients:** 7.6 s and 7.3 s on 2026-10-05 (two runs), 7.0 s on 2026-10-04 (9.7 s with the endpoint's first routing rule, 21 s before the tuning): the Sentinels need about 4.5 s (`down-after 3 s`, agreement, promotion), the endpoint about 2 s more (the new primary's own check, then two Sentinels naming it).
- **A restarted member claims to be a master** until the Sentinels make it a replica again (some seconds). The endpoint sends it nothing in that time: a member is used only while the Sentinels name it.
- **Its start file is static** (`include redis.conf`, root's): Redis cannot rewrite it. Until this drill a member that had been through a failover could not restart — the rewritten file declared every login a second time and loaded the image's bundled modules a second time. See `roles/redis/README.md`.
- **Planned change** (`--tags redis`) with the same endpoint rule: about 3 s of refused connections after the pause.
