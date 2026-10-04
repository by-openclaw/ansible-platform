# role: dbproxy (Docker)

The **data endpoint** (services/0004): the one address consumers connect to. HAProxy routes
PostgreSQL connections to the member Patroni reports as leader. TCP routing only — no pooling,
no TLS termination: the client's TLS session ends on PostgreSQL, whose wildcard certificate is
valid for the endpoint's name, so `sslmode=verify-full` works unchanged.

Run: `ansible-playbook playbooks/dbproxy.yml`.

- **Leader detection**: an HTTPS check of each member's Patroni REST API (`GET /primary`,
  certificate verified); a member is out after `dbproxy_check_fall` failed checks and its
  sessions are closed at once, so clients reconnect to the new leader.
- **Container** (through `roles/service_scaffold`): pinned `dbproxy_image` (HAProxy LTS),
  read-only root filesystem, no capability; the configuration is checked with `haproxy -c`
  before it reaches the running endpoint and re-read on SIGHUP without dropping sessions.
- **Metrics**: HAProxy's built-in Prometheus exporter on `dbproxy_metrics_port`; the platform
  keeps `haproxy_backend_active_servers` / `haproxy_server_status` (rule
  `PostgresEndpointNoLeader`).
- **What it costs**: PostgreSQL sees the endpoint's address as the client's. The connection
  log still names the role and the database, and every service has its own role.
- **Single guest**: stateless, restarts in seconds; while it is down consumers cannot reach
  the leader (the members themselves stay reachable for administration).
