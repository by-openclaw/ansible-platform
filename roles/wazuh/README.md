# role: wazuh

Security monitoring (SIEM/XDR) on `lxc-wazuh-01`: the vendor's single-node deployment (manager, indexer, dashboard) with the platform's contracts on top, and `roles/wazuh_agent` on every guest.

## Contract map

| Concern | How |
|---|---|
| Image pins | `wazuh_version` drives the three images; the certificate generator is pinned separately. Agents pin the same version (an agent must not be newer than its manager). |
| Secrets | Vault `prod/wazuh/admin` (indexer admin), `/dashboard` (kibanaserver), `/api` (wazuh-wui), `/agent-enrol` (authd password) — get-or-create by the role; `/oidc` minted by `roles/authentik`. Hashes in `internal_users.yml` use a salt derived from the password so a re-run renders the same file. |
| TLS | Between the components: the vendor's internal PKI generated once (`generate-indexer-certs.yml`, pinned generator). Edge: the dashboard speaks HTTP on the SVC address behind Traefik (SEC-28); the indexer API stays on loopback. |
| SSO | Native OpenID: the dashboard (`opensearch_dashboards.yml`) and the indexer security plugin (`config.yml`, order 1) authenticate people against Authentik; the `groups` claim maps the platform admin group to `all_access` (`roles_mapping.yml`). Service accounts stay internal (order 0). Security config changes after the first start are pushed with the vendor's `securityadmin` (drift-gated). |
| Agents | apt repository pinned, package held; `ossec.conf` rendered (FIM on the system paths, syscollector, SCA, journald), enrolment with the Vault password read once for the fleet; `wazuh-control status` proves the agent runs. |
| Firewall | catalog aliases `host4/host6_wazuh`, `port_wazuh_dashboard`, `port_wazuh_agent`; rules 1091–1094 (Traefik → dashboard; DMZ guests → manager). Host ufw: agents from the platform supernet, dashboard from Traefik/VPN. |
| Backup | class A: indexer data + manager volumes in the PBS guest image (`docs/backup.md`). |
| Lifecycle | `-e wazuh_state=absent` stops the stack; volumes and Vault paths stay (archive rule); the guest is removed by Terraform. |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/wazuh.yml
```

## Runbook

- Indexer health: `curl -sk -u admin:… https://127.0.0.1:9200/_cluster/health` on the guest (green/yellow on a single node).
- Agents: dashboard → Agents; on a guest `/var/ossec/bin/wazuh-control status`, `/var/ossec/logs/ossec.log` for enrolment errors (wrong password → "Invalid password").
- A changed group mapping or OpenID setting: re-run the play; the role pushes it with `securityadmin`.
- First deployment only: `--check` fails on the Vault secrets (get-or-create cannot mint under check mode).
