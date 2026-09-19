# role: alertmanager

Prometheus Alertmanager on `lxc-monitoring-01` (Debian package `prometheus-alertmanager`, loopback `127.0.0.1:9093`, clustering off). Delivers the prometheus role's alerts by mail through the platform relay and to the Discord channel `#alerts`.

## Contract map

| Concern | How |
|---|---|
| Secrets | mail relay from Vault `prod/monit/smtp-resend` (the same credentials and recipient as the firewall's Monit alerts); Discord webhook from Vault `prod/discord/webhook-alerts`, minted by `roles/discord_guild` (channel `alerts`). Read-only here (`vault_secret_init: {}`); rendered into the config (root:prometheus 0640, `no_log`). |
| Routing | one receiver `platform-ops` (mail + Discord), grouped by alert name and instance; critical repeats hourly, the rest every 4 h; a critical inhibits warnings on the same instance; `ResolverDown` inhibits the probe storm it causes. |
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
- Mail not arriving: the relay rejects unverified from-domains; the from address must belong to the verified domain in the relay account.
