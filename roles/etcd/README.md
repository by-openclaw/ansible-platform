# role: etcd (Docker)

One member of the consensus store the PostgreSQL cluster elects its leader in (Patroni's
DCS). Colocated on the PostgreSQL guests (services/0004) — three members, quorum 2.

Applied by `playbooks/postgresql.yml` (first play, **all members at once**: a member is only
healthy when a quorum is up).

- **Container** (through `roles/service_scaffold`): pinned `etcd_image`, runs as uid
  `etcd_uid` on a host directory it owns (`/var/lib/etcd`, `0700`), read-only root filesystem,
  no capability. Client port `2379` on the member's service address + loopback, peer port
  `2380` on the service address.
- **TLS**: client and peer traffic use the shared wildcard certificate. Peers are **not**
  authenticated by certificate — the wildcard is a server certificate (the public CA no longer
  issues the client-auth usage) — so the peer port is restricted to the members by the
  DOCKER-USER catalog.
- **Authentication**: enabled on the cluster; the `root` user's password is in Vault
  (`etcd/root`, get-or-create) and is what Patroni presents. The password is passed on stdin
  or in the task environment, never on a command line.
- **Housekeeping**: periodic auto-compaction (`etcd_auto_compaction_retention`).
- **Lifecycle**: `-e etcd_state=absent` removes a member's container and data (a member that
  rejoins must start empty).

Check: `docker exec etcd etcdctl --endpoints=<member urls> --cacert /etc/ssl/certs/ca-certificates.crt endpoint health`.
