# roles/postgres_exporter

Prometheus metrics for the shared PostgreSQL cluster, as a pinned container beside it.

Why it exists: on 2026-09-22 the cluster exhausted its connection ceiling twice (09:22Z, 13:27Z) and the
first thing anyone saw was every service behind the identity provider answering 500. Nothing watched the
database. The exporter feeds two alerts that fire on the cause instead of the symptom:

| Alert | Fires on |
|---|---|
| `PostgresConnectionsNearMax` | backends above 80 % of `max_connections` for 5 min |
| `PostgresConnectionsCritical` | above 95 % for 1 min — the state that took the platform down |

Access is least-privilege: its own role with `pg_monitor` and nothing else, password minted in Vault
(`{env}/postgresql/exporter`), TLS enforced (`sslmode=require`).
