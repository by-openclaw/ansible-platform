# role: seaweedfs (S3)

SeaweedFS **4.44** (native binary, master+volume+filer+S3 combined) on `lxc-seaweedfs-01`. The platform S3 (`s3.<domain>`, internal) for GitLab, Harbor blobs, Nextcloud primary, PBS datastore, JumpServer recordings, backups. Memory raised to **4G** after nightly OOM during the PBS ingest burst.

- Data = ZFS `tank/data/seaweedfs` **bind-mounted at `/data`** (created by `pve_zfs_mount`) — deliberately outside the LXC rootfs.
- Per-service buckets + scoped identities via the `seaweedfs_bucket` concern-role.
- Admin UI Authentik-gated via Traefik; offsite `filer.backup` → Contabo (`seaweedfs-backup.service`).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/seaweedfs.yml`

## Backup & restore

Class **C ⚠**: `/data` is a bind-mount and is **NOT in vzdump** — the Contabo offsite sync IS the backup; the guest itself is disposable (class D). Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `systemctl is-active seaweedfs seaweedfs-backup`; S3 `GET /` on :8333 answers (403 unauth = up).
- Logs are noisy (`filer_pb_tail`) — filter `grep -v filer_pb_tail` before reading journal.
- Common: OOM under ingest → check `MemoryMax`/LXC memory; offsite lag → `journalctl -u seaweedfs-backup`.
