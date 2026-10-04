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

## Failover budget (tuned 2026-10-04)

What a client sees when a member dies, and what the time is made of. The first production figures (39 s, 21 s, 6 s) were Patroni's, HAProxy's and Vault's cautious defaults.

| Service | Detection | Takeover | The endpoint or the edge follows |
|---|---|---|---|
| PostgreSQL | the leader key expires: `ttl 10` (`loop_wait 3`, `retry_timeout 3`) | Patroni promotes the synchronous standby | checks every second, two good answers |
| Redis | the Sentinels: `down-after 3 s`, quorum 2 | a Sentinel promotes the replica | checks every second; a member is used only while it says master **and** two Sentinels name it |
| Vault | raft heartbeat (`performance_multiplier 1`) | raft election | the edge checks `/v1/sys/health` every second |
| Authentik | — (two active instances) | — | the edge checks readiness every 2 s |

- **Why Redis no longer waits 18 s:** the wait kept a restarted old primary (it claims to be a master until the Sentinels demote it) out of rotation. The route now asks the Sentinels themselves (`backend redis_named_<member>`): such a member gets no traffic at all, immediately.
- **The floors:** Patroni's `retry_timeout` is also how long an etcd hiccup may last before the leader steps down, and the Sentinels' `down-after` how long a member may be silent — lower values turn a slow second on the hypervisor into a failover.
- **Single instances** (this endpoint, the edge, the resolver, the object store, GitLab, …) have no failover: their time is a restart.
- **Proof:** `playbooks/ha-drill.yml --tags postgresql-kill` / `redis-kill` kill the leader's / the primary's container and measure the gap with a probe that runs three times a second on another host.
