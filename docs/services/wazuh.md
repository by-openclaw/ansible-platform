# Wazuh — Setup Runbook

Security monitoring for every guest: file integrity, log analysis, system inventory, vulnerability detection, security configuration assessment. Answers NIS2 Art. 21 (incident handling, monitoring) and the ISO 27001 A.8.15/A.8.16 lines of the security-stack document.

## 1. Image decision

Wazuh 4.14.x, the vendor's `wazuh-docker` single-node layout pinned by `wazuh_version`; agents from the vendor apt repository pinned to the same version and held.

## 2. Services architecture

| component | where | port |
|---|---|---|
| manager | `lxc-wazuh-01`, container | 1514 (agents), 1515 (enrolment) on the SVC address; 55000 (API) on loopback |
| indexer (OpenSearch) | same guest, container | 9200 on loopback |
| dashboard | same guest, container | 5601 HTTP on the SVC address, behind Traefik |
| agent | every guest, package | outbound to the manager |

## 3. Pre-requisites

Guest by Terraform (`svc-wazuh.tf`, vmid 512, 10.1.3.197), bootstrapped (identity baseline, hardening). `vm.max_map_count` ≥ 262144 on the node (set to 1,048,576; containers inherit it). The guest is an unprivileged LXC: runc cannot raise `memlock` (dropped) and `nofile` must stay ≤ the guest hard limit (`ulimit -Hn` = 524288 → `wazuh_manager_nofile`). Authentik running (client minted by `playbooks/authentik.yml`).

## 4. Secrets (Vault KV paths)

`prod/wazuh/admin`, `prod/wazuh/dashboard`, `prod/wazuh/api`, `prod/wazuh/agent-enrol` (role, get-or-create), `prod/wazuh/oidc` (Authentik blueprint).

## 5. Certificates

Internal PKI between the components generated once by the pinned vendor generator (`config/wazuh_indexer_ssl_certs`). Edge TLS on Traefik with the platform wildcard. Follow-up for the review pass: issue the internal component certificates from step-ca.

## 6. Configuration source

`roles/wazuh/defaults/main.yml` and the templates under `roles/wazuh/templates` (compose, indexer, security plugin, dashboard, manager `ossec.conf`); agent settings in `roles/wazuh_agent`. The security-plugin templates are derived from the files shipped **inside the pinned image** (`docker run --rm --entrypoint cat <image> /usr/share/wazuh-indexer/config/opensearch-security/<file>`), not from the GitHub copy — role names differ between them (4.14: `manage_wazuh_index`). Re-derive on every version bump.

## 7. Provisioning

`playbooks/wazuh.yml`: play 1 server (secrets, configuration, PKI once, stale-mount detection, stack, security config push on drift or when the index is not initialised, health, agent groups, ufw, scaffold); play 2 agent on every guest (group `docker` on `docker_hosts`, `default` elsewhere).

## 8. Exposure / routing

Internal only: split-DNS `wazuh` → Traefik; firewall rules 1091–1096 (v4 + v6 twins). No public record.

## 9. Installation steps

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/authentik.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/opnsense.yml --check -e '{"opn_fw_only": [...the five wazuh objects...]}'   # then without --check
ansible-playbook -i inventories/prod/hosts.yml playbooks/opnsense-unbound-overrides.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/wazuh.yml          # twice; the second must be changed=0
# first fleet roll-out: every agent runs its FIM/rootcheck/syscollector baseline at start → node load spikes for ~15 min
# (LXCs show the host load; sudo prompts can time out). The agents play is serial: 5; do not stack other plays on it.
ansible-playbook -i inventories/prod/hosts.yml playbooks/contract-audit.yml
```

## 10. Post-install configuration

None by hand. The group mapping and the OpenID domain are declared and pushed by the role.

## 11. Upgrade procedure

Bump `wazuh_version` and `wazuh_agent_version` together (manager first, then agents); a ladder playbook follows the platform pattern when the first upgrade is due.

## 12. Health checks

Indexer `_cluster/health`, dashboard `/api/status`, manager API `/`; contract-audit rows `SVC-WAZUH` and `SVC-WAZUH-AGENT`; HTTPS probe on the route.

## 13. Troubleshooting

| symptom | cause | fix |
|---|---|---|
| agent "Invalid password" on enrolment | `authd.pass` differs from Vault | re-run the play on the guest |
| dashboard login loops | OpenID client or redirect URI | `authentik_oidc_apps` slug `wazuh`, redirect `/auth/openid/login` |
| user signed in but no data | group not mapped | `roles_mapping.yml` → `all_access` backend role = the platform admin group |
| compose refuses to start: `error setting rlimit type 8` / `type 7` | unprivileged LXC: memlock not allowed / `nofile` above the guest hard limit | no memlock in the compose template; `wazuh_manager_nofile` ≤ `ulimit -Hn` |
| indexer answers 503 `OpenSearch Security not initialized` | the vendor one-shot bootstrap aborted (bad security file) | the role runs securityadmin whenever the index is not initialised; fix the file, re-run the play |
| securityadmin: `which: command not found` | the image has no `which` and no JAVA_HOME | the role sets `JAVA_HOME=/usr/share/wazuh-indexer/jdk` |
| a fixed file is on disk but the container still misbehaves | single-file bind mount keeps the old inode after an atomic write | the role compares container vs host checksums and recreates the stack (task "Stale mounts found") |
| dashboard logs every minute `Could not check if the index wazuh-monitoring-… exists due to no permissions` | the dashboard user is not mapped to `manage_wazuh_index` (mapping taken from an older upstream file) | `roles_mapping.yml.j2` = the image's mapping + the admin group |
| dashboard: "This instance has no agents registered" while alerts flow | the signed-in person is not mapped in the **manager API** RBAC (`run_as`) | the role creates the rule IdP group → administrator and links it to role 1 |
| authd `Invalid group: docker` | the agent asks for a group the manager has not created | `wazuh_agent_groups` (server role creates them before agents enrol) |
| agent `syscheckd ... fopen error` on `/etc/vconsole.conf` | FIM follows a dangling symlink of the vendor default set | harmless; ignore list is a review-pass item |

## 14. Identity and access

Authentik OpenID (`platform-admins`). Internal service users only for the components. The local `admin` of the indexer is break-glass (Vault). Two RBAC layers are mapped by the role: the indexer security plugin (`roles_mapping.yml`, group → `all_access`) and the manager API (`run_as`: rule `platform_admins_run_as` → administrator role), because the dashboard runs every API call as the signed-in person.

## 15. Notifications

Mailbox `wazuh@<domain>` via the scaffold. Alerting to the platform channels is a follow-up (Wazuh integrations → mail/Discord), tracked in the review pass.
