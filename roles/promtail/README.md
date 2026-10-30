# role: promtail

Ships journal (+`container` label from the journald docker driver), auditd, and any `promtail_extra_file_jobs` (traefik, harbor, vault audit) to Loki. Runs as `promtail` (groups systemd-journal, adm).

On a brand-new host rerun once if the grafana apt repo races the install.

## Audit label (infra/0006 INF-32)

Security streams carry `audit="true"` (the 90-day class): journal entries of `promtail_journal_audit_units` (sshd, sudo, logind, CrowdSec agent) via a `match` pipeline stage, `auditd`, the Vault audit log, and every syslog listener / extra file job declared with `audit: true` (OPNsense syslog on `lxc-monitoring-01`, Traefik access log). Query: `{audit="true"}`.

## Standard file jobs

`promtail_standard_file_jobs` (defaults) ships the files a product writes outside the journal on any guest: the CrowdSec agent log and the Lynis report, both audit-class. Group-specific files stay in `promtail_extra_file_jobs` (group_vars); the two lists are rendered together. Census 2026-10-30: these two were the only recently written files under /var/log that no job covered (sudo.log is a duplicate of the journal's sudo lines).
