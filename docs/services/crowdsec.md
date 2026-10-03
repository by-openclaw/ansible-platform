# CrowdSec — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: crowdsec`). Role `roles/crowdsec` (the engine: LAPI, hub, bouncer registrations, the firewalls' syslog feed) + `roles/crowdsec_agent` (every host) + the bouncers (`roles/traefik` plugin, the OPNsense catalog), play `playbooks/crowdsec.yml` (+ `crowdsec-agents.yml`), guest `lxc-crowdsec-01`. Audit: [`docs/audits/crowdsec-2026-10-03.md`](../audits/crowdsec-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — no user interface (`sso: none`); machines authenticate to the LAPI with per-host machine credentials (`cscli machines`), bouncers with API keys; the CrowdSec Console (SaaS, community plan) holds the enrolment.
2. **Authentik application:** none.
3. **Access model:** 32 machines (every managed host's agent, validated at registration through the role), two bouncers (`opnsense-firewall`, `traefik`); CAPI sharing + community blocklist enabled; operators use `cscli` on the host (SSH baseline) and the Console.
4. **Vault paths:** `secret/{env}/crowdsec/*` — bouncer keys (`crowdsec_bouncer_vault_paths`), the CAPI credentials (`credentials`), agent registration token; the machines' credentials live on each host (0600) as the agent role writes them.
5. **Ansible adapter + vars:** `roles/crowdsec` (`defaults/main.yml`: pin `crowdsec_version`, LAPI, AppSec, collections, syslog feeds, bouncers, whitelists, metrics, firewall; `tasks/config.yml` acquisitions + the Suricata EVE bridge parser; `tasks/bouncer.yml`, `collections.yml`, `token.yml`), `roles/crowdsec_agent` (per host: collections, file datasources).
6. **Removal notes:** `playbooks/decommission-service.yml`; class B — the LAPI database (sqlite, decisions/alerts/machines) in the PBS guest image; bouncers fall back to no decisions when the LAPI is gone.

## Notifications (services/0005)

1. **Transport:** none configured in CrowdSec itself (no notification plugin active): decisions act through the bouncers; alerts are visible in `cscli` and the Console.
2. **What is sent:** nothing by mail.
3. **Alerting path:** Prometheus `node`, `cadvisor` and the engine's `/metrics` (`:6060`: LAPI decisions, alerts, acquisition lines, bouncer pulls) → Alertmanager → Discord/mail; the blackbox probe does not apply (no HTTP front).
4. **Logs:** the engine container on journald → promtail → Loki; the firewalls' Suricata EVE arrives as syslog (`:1515/udp`) and is parsed by the hub collection.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B (`docs/backup.md`): the LAPI database (`/var/lib/crowdsec/data/crowdsec.db`, machines, bouncers, decisions) and the hub state inside the PBS guest image (daily); the engine's configuration is this role. Restore = play + PBS image (or re-registration of every agent and bouncer through their roles).
