# Traefik — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: traefik`). Role `roles/traefik` (+ `roles/traefik_route` as every service's route concern, `roles/lego_cert` for the wildcard), play `playbooks/traefik.yml`, guest `lxc-traefik-01`. Audit: [`docs/audits/traefik-2026-10-03.md`](../audits/traefik-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — the dashboard sits behind Authentik forwardAuth (embedded outpost, application `traefik-dashboard`, proxy provider `forward_single`) and the admin-desk allow-list; every other application's forwardAuth or OIDC is declared by its own route (`traefik_route_forward_auth`).
2. **Authentik application:** `traefik-dashboard` (`group_vars/all/sso.yml`), bound to the group `traefik-admins`.
3. **Access model:** `traefik-admins` → the dashboard (`api@internal`, read-only API); no local accounts; the CrowdSec bouncer middleware runs on the HTTPS entry point before any application; the admin allow-list (`group_vars/all/traefik.yml` `_admin_desk_cidrs`) gates the dashboard route.
4. **Vault paths:** `secret/{env}/cloudflare/<domain>` (the DNS-01 token for the wildcard, `roles/lego_cert`), the CrowdSec bouncer key (`crowdsec_bouncer_vault_paths.traefik`), `traefik-dashboard` outpost config lives in Authentik.
5. **Ansible adapter + vars:** `roles/traefik` (`defaults/main.yml`: pin `traefik_version`, entry points, HSTS/headers, TLS floor, metrics, CrowdSec plugin, firewall; `templates/traefik.yml.j2` static config, `templates/dynamic.yml.j2` platform middlewares + dashboard; `tasks/plugin.yml` vendors the bouncer plugin; `tasks/cert.yml` the wildcard). Every service adds its own file under `/etc/traefik/dynamic/` through `roles/traefik_route`.
6. **Removal notes:** not removable while routes exist — the single edge of the platform. Rebuild = play (wildcard from the lego store, routes re-rendered by every service play).

## Notifications (services/0005)

1. **Transport:** none — Traefik sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus — `node`, `cadvisor`, the `traefik` job (`/metrics` on the dedicated entry point, entry-point/router/service labels) and the blackbox probes of every route → Alertmanager → Discord/mail.
4. **Logs:** access log (`/var/log/traefik/access.log`, `audit` label, 90 d) and the error log → promtail → Loki; CrowdSec agent parses the access log (`crowdsecurity/nginx` collection) and the bouncer enforces the decisions in-line.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class D (`docs/backup.md`): configuration = this role + every service's route file (re-rendered by their plays); the wildcard certificate lives in the lego store (`/etc/lego`, re-issuable through DNS-01); the guest image in PBS is a convenience. Restore = re-run `traefik.yml`, then the service plays (routes).
