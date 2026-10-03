# AdGuard Home (resolver front) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: adguard`). Role `roles/adguard`, play `playbooks/adguard-prod.yml`, guest `vm-adguard-01` (VM). Chain: clients → AdGuard (filtering, DoT/DoQ) → the firewall's Unbound → dnscrypt (`docs/` DNS chain). Audit: [`docs/audits/adguard-2026-10-03.md`](../audits/adguard-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — AdGuard Home has no OIDC/LDAP: `sso: local` with one local administrator; the UI is reached through the platform edge only.
2. **Authentik application:** none (the edge route may carry forwardAuth; the application login stays local).
3. **Access model:** local user `admin` (password in Vault; 5 attempts then a 15-minute block); the UI listener `:3000` admits the edge hosts only (host firewall); DNS `:53` and DoT/DoQ `:853` serve the platform networks.
4. **Vault paths:** `secret/{env}/adguard/admin` (the UI credential, bcrypt hash rendered into the configuration).
5. **Ansible adapter + vars:** `roles/adguard` (`defaults/main.yml`: pin `adguard_version`, listeners, upstreams (the firewall's Unbound), filters, TLS; `templates/AdGuardHome.yaml.j2` = the whole configuration; `tasks/cert.yml` + `lego-renew-adguard.timer` the Let's Encrypt certificate; `tasks/cache_flush.yml`; `tasks/network_ra.yml` (no RA-learned resolvers on the host)).
6. **Removal notes:** not removable — every guest resolves through it (`reference: guest resolver baseline`); a rebuild = play (configuration is code; statistics/query log are local history).

## Notifications (services/0005)

1. **Transport:** none — AdGuard sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus `node` + the blackbox DNS probes (`blackbox_dns_v4`/`v6` resolve through it) → Alertmanager → Discord/mail; no native `/metrics` (an exporter is the monitoring pass's item).
4. **Logs:** the container on journald → promtail → Loki; the query log (90 days) and statistics stay on the guest (volume and privacy: not shipped).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class D (`docs/backup.md`): configuration = this role; the query log and statistics are operational history (in the PBS guest image, not restored on purpose). Restore = re-run `adguard-prod.yml`.
