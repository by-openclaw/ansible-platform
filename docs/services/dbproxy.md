# Data endpoint (dbproxy) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: dbproxy`). Role `roles/dbproxy`, play `playbooks/dbproxy.yml`, guest `lxc-pgpool-01`. The one address consumers connect to for [PostgreSQL](postgresql.md) and [Redis](redis.md): HAProxy routes PostgreSQL to the member Patroni reports as leader and Redis to the member that answers as primary (TCP routing — no pooling, no TLS termination). The same guest runs the third Redis Sentinel.

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — no user interface (`sso: none`); the client's TLS session and its login end on PostgreSQL / Redis themselves. Its one credential is the Redis check login (`INFO` and `PING` only). The wildcard certificate PostgreSQL presents is valid for the endpoint's name (`sslmode=verify-full` unchanged).
2. **Authentik application:** none.
3. **Access model:** the listener is reachable from the consumers' hosts only (DOCKER-USER catalog: `db: shared-pg` services); the leader check reads each member's Patroni REST API over HTTPS (`GET /primary`, certificate verified, no credential — the endpoint is read-only). PostgreSQL sees the endpoint's address as the client's; the connection log still names the role and the database.
4. **Vault paths:** `secret/{env}/redis/users/healthcheck` (read; owner: `roles/redis`).
5. **Ansible adapter + vars:** `roles/dbproxy` (`defaults/main.yml`: pin `dbproxy_image`, check timing `dbproxy_check_*`, idle timeout, metrics port; `templates/haproxy.cfg.j2`; `tasks/main.yml`: configuration checked with `haproxy -c`, container through the scaffold, "exactly one member routed to" asserted).
6. **Removal notes:** removable only after every consumer points back at a member; stateless (no data, no secret).

## Notifications (services/0005)

1. **Transport:** none — sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus job `dbproxy` (HAProxy's exporter, `:8405`, two metric families kept) + `node` + `cadvisor` → `PostgresEndpointNoLeader`, `RedisEndpointNoPrimary` → Alertmanager → Discord/mail.
4. **Logs:** connection log (client, member, duration) and health-check transitions on stdout → journald → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class E (`docs/backup.md`): no data. The guest is in the PBS job; rebuild = the play.

## Failover budget (tuned 2026-10-04, measured again 2026-10-05)

What a client sees when a member dies, and what the time is made of. Measured by `playbooks/ha-drill.yml --tags postgresql-kill | redis-kill | vault-kill`: the member's container is killed and the gap is read from the services' own records: from the container's recorded end to the first record that clients are served again (PostgreSQL and Redis: the endpoint's log line `Server <backend>/<member> is UP`, for Redis also the Sentinels naming the new primary; Vault: the new active node's `active_time`). No probe loop runs. The 2026-10-05 run was made in the evening with nothing else running on the platform.

| Service | Measured (member killed) | Before | Detection | Takeover | The endpoint or the edge follows |
|---|---|---|---|---|---|
| PostgreSQL | **24.4 s** (2026-10-05; the same on 2026-10-04) | 39 s | the leader lock expires: `ttl 20` (`loop_wait 3`, `retry_timeout 8`) | Patroni promotes the synchronous standby (no write lost) | checks every second, two good answers |
| Redis | **7.6 s** (2026-10-05; 7.0 s on 2026-10-04; 9.7 s with the first routing rule) | 21 s | the Sentinels: `down-after 3 s`, quorum 2 | a Sentinel promotes the replica | checks every second, one good answer; a member is used only while it says master **and** two Sentinels name it |
| Vault | **2.4 s** until another member is active (2026-10-05); a client saw 3.4 s on 2026-10-04, the edge's check included | 6 s | raft heartbeat (`performance_multiplier 1`) | raft election, then the new active node loads its state | the edge checks `/v1/sys/health` every second |
| Authentik | — (two active instances; not part of this run) | — | — | — | the edge checks the liveness path every 2 s |

- **`retry_timeout` is not part of the failover time:** it is how long the leader may fail to reach the consensus store before it steps down by itself. 8 s is the most a 20 s lock allows (`loop_wait + 2 x retry_timeout <= ttl`); with 3 s the leader stepped down on 2026-10-05 00:00:47 UTC during a stall of its own guest.
- **PostgreSQL's floor is Patroni's:** `ttl` cannot be lower than 20 s (a lower value is raised to 20 without a message; etcd shows the lock's granted lifetime). A lost leader — the whole member, Patroni included — is therefore replaced after about 20 s plus the promotion and the endpoint's check. A planned switchover takes about a second; PostgreSQL crashing under a living Patroni is handled by Patroni at once.
- **Sessions of a former configuration:** a reload starts a new worker; the former one keeps the sessions it holds and no longer checks the members, so a dead member does not end them. `hard-stop-after` ({{ dbproxy_hard_stop_after }} in the role) bounds that: the former worker closes its sessions and the clients reconnect to the worker that watches. The role restarts the endpoint once when a worker without that bound is still present.
- **The configuration is validated before it lands:** the pinned image parses the rendered file before it replaces the one on disk.
- **Why Redis no longer waits 18 s:** the wait kept a restarted old primary (it claims to be a master until the Sentinels demote it) out of rotation. The route now asks the Sentinels themselves (`backend redis_named_<member>`): such a member gets no traffic at all, immediately.
- **The floors:** Patroni's `retry_timeout` is also how long an etcd hiccup may last before the leader steps down, and the Sentinels' `down-after` how long a member may be silent — lower values turn a slow second on the hypervisor into a failover.
- **Single instances** (this endpoint, the edge, the resolver, the object store, GitLab, …) have no failover: their time is a restart.
- **Proof:** the three kill drills above; the Redis drill also asserts that the restarted former primary received no session (counted by the time a session was accepted — the endpoint logs a session when it ends).
- **Incident 2026-10-04 17:45:34–17:49:15 UTC:** the first version of the Sentinel check ended with `QUIT`, which a Sentinel does not answer for the restricted check login; every Sentinel check timed out, no member was "named", and the endpoint refused Redis connections. The role's own verification failed the play, but after the reload. The check now ends on the Sentinel's answer.
