# role: pbs (Proxmox Backup Server)

PBS **4.2.5** on `vm-pbs-01` (SVC `10.1.3.222`), S3-backed datastore on SeaweedFS. Second nightly copy (01:30) alongside the NFS vzdump. Backup identity `svc-pbs-backup-prod@pbs!pve` (DatastoreBackup only); **client-side encryption**, key custodied in Vault `prod/pbs/encryption-key`.

- `playbooks/pbs-pve-storage.yml` wires PVE: user/token/ACL, storage (converges creds on drift), the job, PBS self-exclusion, `freeze-fs-on-backup=0` for OPNsense.
- Jobs (declared in `pbs_jobs`, converged — not create-only): `prune` daily (keep 3/14/8/6), `verify` daily at 21:00 UTC (new snapshots within a day, re-verify after 30d), GC daily. Notifications: root@pam's address = `platform_alert_email` (built-in mail-to-root target; failures and job results). Authentik OIDC realm for the UI.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/pbs.yml`

## Backup & restore

Class **A**: excluded from its own S3 job; DR copy = NFS `vzdump-qemu-103`. Restores are the platform's restore path (file-level drill proven). Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `proxmox-backup-manager datastore list`, `verify-job list`, `task list`; from PVE `pvesm status --storage pbs` active.
- Restore: `proxmox-backup-client restore <snapshot> <archive> <dest> --keyfile /etc/pve/priv/storage/pbs.enc` — set `PBS_FINGERPRINT` or the client **prompts and hangs**.
- Common: `backup owner check failed` after an identity change → `change-owner` the groups (temporary DatastoreAdmin); unpriv-CT backups from an Ansible shell → `umask 022`.
