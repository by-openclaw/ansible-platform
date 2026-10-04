# role: redis_sentinel (Docker)

One of the **three Sentinels** that watch the Redis pair (services/0004) and promote the
replica when the primary is gone: one on each Redis member, one on the endpoint guest. A
quorum of 2 agrees before a failover.

Applied by `playbooks/redis.yml` (second play).

- **Container** (through `roles/service_scaffold`): the same pinned image as the members,
  started as the redis uid, read-only root filesystem, no capability. TLS only (`tls-port
  26379`), its own password (Vault `redis/sentinel`).
- **Configuration**: Sentinel OWNS `sentinel.conf` once it runs — it records the members, the
  other Sentinels and the failover epochs in it. The role writes the file only when it does
  not exist (asking the members which one is the primary at that moment);
  `-e redis_sentinel_reset=true` re-creates it.
- **Names, not addresses**: `resolve-hostnames` / `announce-hostnames` — members and Sentinels
  are known by their FQDN, which is also what their certificate carries.
- **Timing**: a primary silent for `redis_sentinel_down_after_ms` (5 s) is suspected; with the
  election a failover completes in well under a minute.
