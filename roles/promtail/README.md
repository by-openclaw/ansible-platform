# role: promtail

Ships journal (+`container` label from the journald docker driver), auditd, and any `promtail_extra_file_jobs` (traefik, harbor, vault audit) to Loki. Runs as `promtail` (groups systemd-journal, adm).

On a brand-new host rerun once if the grafana apt repo races the install.
