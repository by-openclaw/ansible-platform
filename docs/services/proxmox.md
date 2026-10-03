# Proxmox VE (hypervisor) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: proxmox`). Role `roles/pve_host`, plays `playbooks/pve-host.yml` (converge) and `playbooks/pve-host-upgrade.yml` (release ladder), node `srv-proxmox-poc-01` (the live platform's single node). Audit: [`docs/audits/proxmox-2026-10-03.md`](../audits/proxmox-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — OpenID Connect realm `authentik` (issuer = the Authentik application `proxmox`, `autocreate`, `username-claim email`, `groups-claim groups` with `groups-overwrite`): people sign in through Authentik, their PVE groups follow the IdP on every login.
2. **Authentik application:** OIDC confidential client, slug `proxmox` (`group_vars/all/sso.yml`), redirect `https://proxmox.<domain>`; access bound to the group `proxmox-admins`.
3. **Access model:** `proxmox-admins` (Authentik) → PVE group `proxmox-admins-authentik` → `Administrator` on `/`. Local realms: `<org>@pam` (the OOB/break-glass admin, identity/0004: Linux account + password in Vault, sudo), `root@pam` (PVE's own root — kept enabled because PVE needs it for cluster/host operations, no SSH login, password in Vault `proxmox/root`). Automation (declared in `pve_host_service_accounts`, `pve` realm, no password, privilege-separated tokens): `svc-rune@pve!terraform` (`TerraformRole` — infra-terraform-proxmox), `svc-rune@pve!admin` (`Administrator` — platform automation, Vault `proxmox/admin`), `svc-opus@pve!audit` (`PVEAuditor`, read-only). ACL entries on these identities that are not declared are removed by the role.
4. **Vault paths:** `secret/{env}/pve/oidc` (the client, minted by `roles/authentik`), `proxmox/admin`, `proxmox/root`, `proxmox/tokens/<user>-<token>` (tokens minted by the role), `pbs/pve-backup-token` (the PBS storage credential — `pbs-pve-storage.yml`).
5. **Ansible adapter + vars:** `roles/pve_host` (`defaults/main.yml`: repositories, the release pin `pve_host_version`, datacenter options, firewall ipsets/rules, OIDC realm, ACLs, roles, service accounts, backup jobs, configuration export, static routes, WAN bridges; `tasks/identity.yml` reconciles realm/users/roles/tokens/ACLs; `tasks/firewall.yml` the datacenter + host firewall; `tasks/backup_jobs.yml` the NAS job; `tasks/config_backup.yml` the export to PBS). `playbooks/pbs-pve-storage.yml` wires PBS as a storage + the second guest backup job.
6. **Removal notes:** not a removable service — the node hosts every guest. A node rebuild = Terraform/PVE install + `pve-host.yml` + `pbs-pve-storage.yml`; the configuration export (PBS host backup) restores `/etc/pve`, `/etc/network`, `/etc/apt`.

## Notifications (services/0005)

1. **Transport:** the node's postfix (hardening relay → the mail host) as `email_from` = the alerts mailbox; vzdump mails (`mailnotification always`) to the ops address.
2. **What is sent:** backup job results (NAS job daily; the PBS job reports through PBS), PVE system mails to root.
3. **Alerting path:** Prometheus `node` job (`:9100`, scraped from the monitoring host through the datacenter firewall) → Alertmanager → Discord/mail. No PVE-native `/metrics` yet (a `pve-exporter` with a `PVEAuditor` token is the monitoring pass's item).
4. **Logs:** journald → promtail → Loki; the UI/API access log and the task log with the `audit` label, the datacenter firewall log (drops, `log_level_in info`) the default class (`group_vars/proxmox_nodes.yml`). auditd + Wazuh agent + CrowdSec agent on the node.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class A (`docs/backup.md`): the hypervisor's configuration — `/etc/pve`, `/etc/network`, `/etc/apt` — exported daily (04:30) as a PBS **host backup** of the node (`pve-config-backup.timer`), encrypted with the PBS storage's key, with the storage's token; verified by `proxmox-backup-client snapshot list`. The guests are backed up by the two vzdump jobs (NAS 05:00 keep-all — retention = owner item; PBS 03:30, pruned on PBS, replicated to S3). Restore = reinstall + `pve-host.yml`, then `proxmox-backup-client restore host/<node>/<snapshot> pve-etc.pxar /etc/pve` (pmxcfs stopped) and the guests from PBS.

The guests' NAS copy (job at 05:00 on the NFS storage) keeps **7 daily, 4 weekly and 6 monthly** backups per guest (`pve_host_nfs_backup_prune`, owner decision 2026-10-03); the job prunes after each run. Backups of guests that no longer exist are not pruned by the job.
