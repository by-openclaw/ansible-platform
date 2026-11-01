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

PBS is the second, off-site copy (3-2-1 with the NAS copy): datastore `pbs-s3` on Contabo S3 directly (PBS 4 S3 backend, a local cache on the guest), every snapshot client-side encrypted (key in Vault), prune daily (keep 1 last / 14 daily / 8 weekly / 12 monthly), GC daily (00:00Z), verify weekly (Sunday 06:00Z, a snapshot is re-read after 90 days). Its own state: `/etc/proxmox-backup` (users, ACLs, jobs, datastore definition) inside the VM image → the NAS vzdump job; the datastore needs no backup of its own (it is the backup). Restore of PBS = redeploy the VM + `pbs.yml` + `pbs-pve-storage.yml`; the S3-backed datastore re-attaches to the bucket with the key from Vault.

### Operating rule — the provider's line is the limit

Contabo documents 250 API requests/s and 10 MB/s (80 Mbit/s) for the account. Every chunk the verify or a restore needs comes back over that line: the weekly verify re-reads nearly the whole deduplicated set (~490 GB) and takes ~15 h (measured 2026-10-31 22:00Z → 11-01 13:19Z); a 20 GB guest restored from PBS alone takes ~35 min — the NAS copy is the fast restore source, PBS the off-site one. Two controls keep PBS under the cap, both declared in `platform_external_s3` and applied by `roles/pbs` to the S3 endpoint: `limit-active-requests` (25 PUT/POST/DELETE per second) and `limit-passive-requests` (100 GET/HEAD per second). The verify runs after the backup window so the uploads and the verify's reads never share the line: started Saturday 22:00Z it ran through Sunday's backups and five healthy snapshots were marked `failed` by 429 answers (2026-11-01 04:43–05:01Z). A 429 the S3 verify receives is not retried (upstream #7606 pending) and marks the snapshot `failed` — a read error, not corruption (the same shape as the 2026-10-02/03 edge restarts on the old on-site datastore, `docs/audits/pbs-2026-10-03.md`).

A snapshot marked `failed` is not picked up again by the verify job: the job skips every snapshot that already carries a verification state until it is outdated (90 days). `ansible-playbook playbooks/pbs-reverify.yml` lists the states; with `-e pbs_reverify_apply=true` it re-verifies each failed snapshot on its own (`ignore-verified` off), one at a time and waiting for each task, then asserts that none is left failed. Not during the backup or verify windows.
