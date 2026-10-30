# role: pbs (Proxmox Backup Server)

PBS **4.2.5** on `vm-pbs-01` (SVC `10.1.3.222`), S3-backed datastore off-site on the provider (infra/0008, 2026-10-20). Second nightly copy (01:30) alongside the NFS vzdump. Backup identity `svc-pbs-backup-prod@pbs!pve` (DatastoreBackup only); **client-side encryption**, key custodied in Vault `prod/pbs/encryption-key`.

- `playbooks/pbs-pve-storage.yml` wires PVE: user/token/ACL, storage (converges creds on drift), the job, PBS self-exclusion, `freeze-fs-on-backup=0` for OPNsense.
- Jobs (declared in `pbs_jobs`, converged — not create-only): `prune` daily (keep 3/14/8/6), `verify` daily at 21:00 UTC (new snapshots within a day, re-verify after 30d), GC daily. Notifications: root@pam's address = `platform_alert_email` (built-in mail-to-root target; failures and job results). Authentik OIDC realm for the UI.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/pbs.yml`

## Backup & restore

Class **A**: excluded from its own S3 job; DR copy = NFS `vzdump-qemu-103`. Restores are the platform's restore path (file-level drill proven). Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `proxmox-backup-manager datastore list`, `verify-job list`, `task list`; from PVE `pvesm status --storage pbs` active.
- Restore: `proxmox-backup-client restore <snapshot> <archive> <dest> --keyfile /etc/pve/priv/storage/pbs.enc` — set `PBS_FINGERPRINT` or the client **prompts and hangs**.
- Common: `backup owner check failed` after an identity change → `change-owner` the groups (temporary DatastoreAdmin); unpriv-CT backups from an Ansible shell → `umask 022`.

## The migrated history lives in a namespace

A PBS sync job carries only the snapshots newer than the newest one already in the target group. The
nightly backups reached the off-site datastore before the old history did, so the history is synced into
its own namespace (`pbs_datastore_migrate_ns`, default `history`) where every group starts empty. The
prune and verify jobs cover it (`max-depth: 7`), so it ages out under the same retention. To restore from
it, add a PVE storage entry for the same datastore with the `namespace` option (and the node's own key),
or use the PBS web interface.

- Node options (`tasks/node.yml`, tags `pbs,node`): `task-log-max-days` from `pbs_task_log_max_days` (30, the Admin Guide's example) — PBS otherwise keeps task logs forever. ISO 27001 A.8.15 logging (bounded retention), A.8.6 capacity.
