# role: alertmanager

Prometheus Alertmanager on `lxc-monitoring-01` (Debian package `prometheus-alertmanager`, loopback `127.0.0.1:9093`, clustering off). Delivers the prometheus role's alerts by mail through the platform relay and to the Discord channel `#alerts`.

## Contract map

| Concern | How |
|---|---|
| Secrets | mail through the platform mail server with the `monitoring@` service mailbox (Vault `prod/mail/monitoring`, mailbox concern-role) to `alerts@<domain>` — the same path as the firewall's Monit; Discord webhook from Vault `prod/discord/webhook-alerts`, minted by `roles/discord_guild` (channel `alerts`). Read-only here (`vault_secret_init: {}`); rendered into the config (root:prometheus 0640, `no_log`). |
| Routing | one receiver `platform-ops` (mail + Discord), grouped by alert NAME only (one notification per alert name, every instance listed inside — grouping by instance too flooded Discord into HTTP 429 during the 2026-09-22 firewall rebuild); 1 min group wait, critical repeats hourly, the rest every 4 h; a critical inhibits warnings on the same instance; a dead resolver inhibits the probe/target alerts it explains. |
| Message format | `files/alertmanager.tmpl`: Discord title = `🔴 FIRING · <alert> · <n> alerts` (🟢 RESOLVED); body = the rule's `description` ("what it means"), its `runbook` ("what to do first"), then one line per instance with its `summary` and start time (25 max). Mail subject = `[<domain>] STATUS <alert> (<n>)`. |
| Exposure | loopback; Grafana has it as a datasource; no route. |
| Validation | `amtool check-config` before every write. |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/discord.yml     # once: creates #alerts + its webhook in Vault
ansible-playbook -i inventories/prod/hosts.yml playbooks/monitoring.yml
```

## Runbook

- Fire a test alert (proves mail + Discord end to end):
  `curl -s -XPOST http://127.0.0.1:9093/api/v2/alerts -H 'Content-Type: application/json' -d '[{"labels":{"alertname":"TestAlert","severity":"warning","instance":"manual"},"annotations":{"summary":"delivery test"}}]'` — resolves itself after 5 min.
- Silence: `amtool --alertmanager.url=http://127.0.0.1:9093 silence add alertname=… --duration=2h --comment=…`.
- Mail not arriving: check the mail server's postfix log for `monitoring@` → `alerts@`; SMTP goes to the asset FQDN (`vm-mailcow-01.<domain>`, 587 STARTTLS), never to `mail.<domain>` (split-DNS → Traefik).
