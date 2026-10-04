# Data endpoint (dbproxy) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: dbproxy`). Role `roles/dbproxy`, play `playbooks/dbproxy.yml`, guest `lxc-pgpool-01`. The one address consumers connect to for [PostgreSQL](postgresql.md): HAProxy routes to the member Patroni reports as leader (TCP routing — no pooling, no TLS termination).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — no user interface (`sso: none`) and no credential of its own: the client's TLS session and its `scram-sha-256` login end on PostgreSQL itself. The wildcard certificate PostgreSQL presents is valid for the endpoint's name (`sslmode=verify-full` unchanged).
2. **Authentik application:** none.
3. **Access model:** the listener is reachable from the consumers' hosts only (DOCKER-USER catalog: `db: shared-pg` services); the leader check reads each member's Patroni REST API over HTTPS (`GET /primary`, certificate verified, no credential — the endpoint is read-only). PostgreSQL sees the endpoint's address as the client's; the connection log still names the role and the database.
4. **Vault paths:** none.
5. **Ansible adapter + vars:** `roles/dbproxy` (`defaults/main.yml`: pin `dbproxy_image`, check timing `dbproxy_check_*`, idle timeout, metrics port; `templates/haproxy.cfg.j2`; `tasks/main.yml`: configuration checked with `haproxy -c`, container through the scaffold, "exactly one member routed to" asserted).
6. **Removal notes:** removable only after every consumer points back at a member; stateless (no data, no secret).

## Notifications (services/0005)

1. **Transport:** none — sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus job `dbproxy` (HAProxy's exporter, `:8405`, two metric families kept) + `node` + `cadvisor` → `PostgresEndpointNoLeader` → Alertmanager → Discord/mail.
4. **Logs:** connection log (client, member, duration) and health-check transitions on stdout → journald → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class E (`docs/backup.md`): no data. The guest is in the PBS job; rebuild = the play.
