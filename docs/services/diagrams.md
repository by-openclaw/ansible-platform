# Diagrams (Kroki, PlantUML, draw.io) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: diagrams`, aliases `kroki`, `plantuml`, `drawio`). Role `roles/diagrams`, play `playbooks/diagrams.yml`, guest `lxc-diagrams-01` (ct 570). Audit: [`docs/audits/diagrams-2026-10-02.md`](../audits/diagrams-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — Kroki and PlantUML are rendering back-ends called server-side by GitLab (and by browsers for the rendered images), draw.io is an editor embedded as an iframe by GitLab and Nextcloud: forwardAuth on an iframe is blocked by browsers, so the draw.io route carries `forward_auth: false` by design (stateless editor, internal-only route); Kroki and PlantUML sit behind the platform forwardAuth.
2. **Authentik application:** forwardAuth (`sso: forwardauth`); no OIDC client of its own.
3. **Access model:** internal-only routes (VPN/LAN); no accounts in the products (stateless renderers/editor).
4. **Vault paths:** none (no secrets).
5. **Ansible adapter + vars:** `roles/diagrams` (`defaults/main.yml`: the four image pins and ports; `tasks/main.yml` = one `service_scaffold` contract: network, four containers with health checks, three routes).
6. **Removal notes:** `playbooks/decommission-service.yml` (`diagrams_state: absent`); class D — stateless.

## Notifications (services/0005)

1. **Transport:** none (`mailbox: false`).
2. **What is sent:** nothing.
3. **Alerting path:** Prometheus blackbox `https://diagrams.<domain>/`-family probes → Alertmanager → Discord/mail (platform); the products expose no Prometheus metrics (Kroki `/health` is the health signal).
4. **Logs:** the four containers → journald → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class D (`docs/backup.md`): stateless (draw.io stores on the user's device, Kroki/PlantUML render on request); the guest image in PBS (daily, ct 570) is a convenience. Restore = re-run the play.
