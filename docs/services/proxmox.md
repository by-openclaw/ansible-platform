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

## Cold start (found and fixed on 2026-10-03)

- **Boot sequence:** every guest carries `startup: order=N,up=S` from `pve_host_boot_order` (`group_vars/proxmox_nodes.yml`): firewall → resolver → Vault + warden → PostgreSQL, Redis, object storage → edge, sign-in, CrowdSec, CA → monitoring, backup server, mail → the applications, heavy ones spread out. The last guest starts ≈5.5 min after boot. A new guest gets a row in that table (the play lists guests without one). Without the sequence every guest started in the same second (load 270 on 12 CPUs, 17 min to settle).
- **Routes of the node:** the route to the guest zones is a `post-up` line of the OOB bridge. The role checks that `ifquery` parses it — a line the network tool cannot parse is silently not run at boot (that happened: the edge could not reach the console after the reboot).
- **After a reboot, check:** `zpool status -x`, every guest running, Vault unsealed (the warden does it within a minute), the firewall health script, Prometheus targets and probes.

## Storage controller (HPE Smart Array P420i, RAID mode)

Every pool disk is a single-drive RAID-0 logical volume; ZFS mirrors pair them. The controller knows bay, health and wear — `ssacli` (installed by the role, `pve_host_smartarray_cli`) reads it:

```
ssacli ctrl slot=0 pd all show status        # physical drives by bay
ssacli ctrl slot=0 ld all show status        # logical volumes (one per pool disk)
ssacli ctrl slot=0 ld <n> show detail        # which array / drive a volume uses
```

- **Read the storage:** `ansible-playbook playbooks/pve-storage-health.yml` — pool state, logical volumes, drives, wear per bay (grown defects, uncorrected errors).
- **A logical volume shows `Failed` while its physical drive is `OK`** (2026-10-03, bay 14, under heavy writes): `playbooks/pve-storage-health.yml -e pve_storage_reenable=true` re-enables the volume, waits for ZFS to resilver from the mirror partner, scrubs the pool and asserts it ONLINE with 0 errors. On 2026-10-03: resilver 35 s, scrub 393 G with 0 errors.
- **A drive (or its bay) is to be taken out of the pool** — failed, or its volume fails again and again (bay 14: 2026-10-03 and 2026-10-07):
  1. fit the new drive in a **free** bay (hot-plug) and leave the old one where it is;
  2. `ansible-playbook playbooks/pve-storage-health.yml -e pve_storage_replace_ld=<volume of the old drive> -e pve_storage_replace_with_drive=<port:box:bay of the new drive>` — first with `--check`. The play creates the new drive's volume, replaces the member, waits for the copy, deletes the old volume on the controller, scrubs, and asserts the pool ONLINE with 0 errors;
  3. pull the old drive when the play says it is used by nothing any more.

  A volume that already exists and that nothing uses can take over instead of a new drive: `-e pve_storage_replace_with_ld=<n>`. The play refuses, before changing anything, a member whose mirror partner is not ONLINE and a replacement that is in use (imported pool, mount, LVM).

  Count about an hour: on 2026-10-08 the copy of one mirror side took 23 minutes (the controller's cache module is disabled) and the scrub 13.
- **Bays, as of 2026-10-08:** the volume of bay 14 failed three times in five days (2026-10-03, 2026-10-07, 2026-10-08) while its drive tested clean; its pool member was moved to a new drive fitted in bay 18 and the volume was deleted. Bay 14 is not to be reused before the bay or that drive is cleared. The volume of bay 15 belongs to no pool (it carried a dead pool's labels, cleared): it is the spare volume already in the chassis (`-e pve_storage_replace_with_ld=<its number>`).
- **Do not reboot the node with a failed logical volume:** the controller can stop at its boot prompt, and the firewall VM lives on this node.
- Alert: `ZfsPoolNotOnline` (Prometheus) fires when the pool is not ONLINE.
- Known state: the controller's cache module is "permanently disabled (backup to flash failed)"; drive write cache is off. Several drives carry grown defects (see the 2026-10-03 addendum of the audit record) — a spare 300 GB SAS drive on site is advised.
