# Redis (shared instance) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: redis`). Role `roles/redis`, play `playbooks/redis.yml`, guests `lxc-redis-01` and `lxc-redis-02` (a primary and a replica) with three Sentinels (`roles/redis_sentinel`: the two members and the endpoint guest); consumers connect to the data endpoint ([dbproxy](dbproxy.md)). Database allocation: `inventories/prod/group_vars/all/redis.yml` (`platform_redis_databases`). Audit: [`docs/audits/redis-2026-10-03.md`](../audits/redis-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — no user interface (`sso: none`); clients authenticate with the instance password over TLS (TLS-only listener, the plain port is closed).
2. **Authentik application:** none.
3. **Access model:** one `default` user for every consumer today (NetBox db 0/1, Authentik db 2, Nextcloud db 3, GitLab db 4 — `platform_redis_databases`); a user per consumer with its own credential is the platform's open item (services/0004: per-service identities). No command is renamed; `protected-mode yes`.
4. **Vault paths:** `secret/{env}/redis/admin` (`host`, `port`, `tls`, `password`) — every consumer reads this document.
5. **Ansible adapter + vars:** `roles/redis` (`defaults/main.yml`: pin `redis_image`, TLS (the platform wildcard), persistence (AOF + RDB), memory policy; `tasks/config.yml` renders `redis.conf` (0640 to the redis uid), `tasks/tls.yml` the certificate, `tasks/container.yml` the container through the scaffold).
6. **Removal notes:** not removable while consumers exist; class E for the caches, B for NetBox's queues — the data volume (`redis-data`, AOF) in the PBS guest image.

## Notifications (services/0005)

1. **Transport:** none — Redis sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus `node` + `cadvisor` → Alertmanager → Discord/mail; a `redis_exporter` (keys, memory, clients per db) is the monitoring pass's item (SVC-33).
4. **Logs:** the container on journald → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class E/B (`docs/backup.md`): caches rebuild; the append-only file and RDB snapshots under the `redis-data` volume are in the PBS guest image (daily). Restore = play + the volume from PBS (or an empty instance: consumers repopulate their caches; NetBox re-queues).
