# Proxmox Backup Server — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: pbs`). Role `roles/pbs`, plays `playbooks/pbs.yml` (converge), `playbooks/pbs-pve-storage.yml` (wires PBS into the hypervisor: storage + the second guest backup job) and `playbooks/pbs-upgrade.yml` (release ladder); guest `vm-pbs-01` (VM 103). Audit: [`docs/audits/pbs-2026-10-03.md`](../audits/pbs-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — OpenID realm `authentik` (issuer = the Authentik application `pbs`, `autocreate`, `username-claim preferred_username`, scopes `openid email profile`); the privileged accounts are pre-created from the admin group in `people.yml` and granted `Admin` on `/`.
2. **Authentik application:** OIDC confidential client, slug `pbs` (`group_vars/all/sso.yml`), redirect `https://pbs.<domain>`; access bound to the group `pbs-admins`.
3. **Access model:** `pbs-admins` (Authentik) → `<user>@authentik` with `Admin` on `/`. `root@pam` = PBS's own superuser (break-glass; no SSH login; the VM's local admin is the hardening baseline). Automation: `svc-pbs-backup-prod@pbs!pve` (`DatastoreBackup` on `/datastore/pbs-datastore` only) is the hypervisor's storage credential — minted by `pbs-pve-storage.yml`, in Vault; the retired `pve-backup@pbs` stays disabled (never deleted, archived).
4. **Vault paths:** `secret/{env}/pbs/oidc` (`roles/authentik`), `pbs/pve-backup-token`, `pbs/encryption-key` (the client-side key every snapshot is encrypted with — DR-critical), `pbs/s3` (the SeaweedFS identity of the `pbs-datastore` bucket, `seaweedfs_bucket`).
5. **Ansible adapter + vars:** `roles/pbs` (`defaults/main.yml`: pin `pbs_version`, datastore, schedules and retention `pbs_keep_*`, OIDC, firewall, notifications; `tasks/datastore.yml` the S3 endpoint + S3-backed datastore, `tasks/jobs.yml` prune/verify, `tasks/oidc.yml`, `tasks/notify.yml`), `playbooks/pbs-pve-storage.yml` (PVE side), `roles/apt_release_ladder` for the release.
6. **Removal notes:** the backup target of the whole platform — not removable while guests exist. The datastore lives in the SeaweedFS bucket `pbs-datastore` (replicated off-site); the encryption key in Vault; the VM itself is in the NAS vzdump job.

## Notifications (services/0005)

1. **Transport:** `mail-to-root` (sendmail → the VM's postfix relay → the mail host) to `root@pam`'s address = the ops mailbox.
2. **What is sent:** job results (prune, GC, verify, sync) and backup task failures.
3. **Alerting path:** Prometheus `node` job + blackbox `https://pbs.<domain>/` → Alertmanager → Discord/mail. No PBS-native `/metrics` (a `pbs-exporter` is the monitoring pass's item).
4. **Logs:** journald (task start/end, proxy) → promtail → Loki; the API access log (`/var/log/proxmox-backup/api/access.log`) with the `audit` label (`group_vars/pbs.yml`).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

PBS is the backup system: datastore `pbs-datastore` S3-backed on SeaweedFS (bucket replicated to the off-site S3 = 3-2-1 with the NAS copy), every snapshot client-side encrypted (key in Vault), prune daily (keep 3/14/8/6), GC daily, verify 21:00 with re-verification after 30 days. Its own state: `/etc/proxmox-backup` (users, ACLs, jobs, datastore definition) inside the VM image → the NAS vzdump job (05:00); the datastore needs no backup of its own (it is the backup). Restore of PBS = redeploy the VM + `pbs.yml` + `pbs-pve-storage.yml`; the S3-backed datastore re-attaches to the bucket with the key from Vault.

### Operating rule — no S3 or edge restart while PBS reads

The datastore reads its chunks from S3 **through the edge** (`s3.<domain>` on Traefik → SeaweedFS). A restart of the S3 server or of the edge during the nightly verify (21:00–22:30Z), the backup run (03:30Z) or a manual verify makes chunk reads fail and marks healthy snapshots `failed` (read errors, not corruption — 2026-10-02 and 2026-10-03, see `docs/audits/pbs-2026-10-03.md`). Applies of `seaweedfs.yml` and `traefik.yml` that recreate a container stay outside those windows.

A snapshot marked `failed` is not picked up again by the verify job: the job skips every snapshot that already carries a verification state until it is outdated (30 days). Re-verify it on its own with `ignore-verified` off (datastore verify API, `backup-type` / `backup-id` / `backup-time` of that snapshot), then confirm that every snapshot reports `ok`.
