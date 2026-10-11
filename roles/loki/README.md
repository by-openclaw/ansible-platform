# role: loki

Loki (a container: `grafana/loki:<loki_version>`, host network, run as the loki account) on `lxc-monitoring-01` (`:3100`, gRPC `:9096`). The Grafana APT source on this host is promtail's (roles/promtail). Every host ships via `promtail` (journal + container labels, auditd, vault_audit, traefik_access/error, harbor_components). Retention ≥30d (audit services ≥90d).

- `/var/lib/loki` = WAL/cache/compactor scratch **only**.
- Query labels: `job`, `host`, `unit`, `container`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/monitoring.yml`

## Backup & restore

Class **E** — retention window; no backup. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `GET /ready`; `curl /loki/api/v1/label/job/values` lists the expected jobs.
- Common: a host missing → `systemctl is-active promtail` there; new file logs → `promtail_extra_file_jobs` in that group's vars.

## Alerts on logs (the ruler)

Loki evaluates the rules of `templates/rules.yml.j2` and sends what fires to the alert manager of
the same host. First use: Vault's audit log (security/0001 §People reading in Vault — what an
administrator of Vault could do by changing a policy is detected, not prevented).

| Alert | Fires when |
|---|---|
| `VaultPersonAreaTouchedByAnother` | a document of a person's area is read, changed or attempted by anyone but that person or automation |
| `VaultPolicyChangedOutsideAutomation` | a policy is written or removed (or attempted) by anyone but the roles' own login |
| `VaultRootTokenInUse` | a request carries a root token, or a root token is being generated |
| `VaultAuditLogSilent` | no audit entry reached Loki for longer than a day |

- A refused attempt is in the audit log too, and counts.
- A new config is checked by the image itself before it replaces the running one (`-verify-config`);
  a rule file is read by the ruler once a minute, without a restart; the role then asks the ruler
  for its list and fails if a declared alert is missing from it.
- The log comes from every Vault member (inventory: `group_vars/vault_cluster.yml`): the active
  member writes it, whichever it is.
