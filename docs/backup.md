# Backup & restore — per-service classes (infra/0008 · INF-41/42/44/45)

Every stateful service declares **one backup class**, its **mechanism**, and its
**restore path** here. This is the authoritative matrix; per-role READMEs link
back to it. 3-2-1 = local (NFS) + PBS (SeaweedFS S3, encrypted) + offsite
(Contabo via SeaweedFS `filer.backup`).

## The universal layer (every guest)

| Job | When | Mechanism | Proof |
|---|---|---|---|
| **PBS** (2nd copy) | 01:30 nightly | `vzdump` → PBS S3 datastore, **client-side encrypted** (key in Vault `prod/pbs/encryption-key`), verify weekly, prune 3/14/8/6, GC daily | 26/26 nightly ✓ · file restore drill ✓ (`ct/501`) |
| **NFS** (1st copy) | 05:00 nightly | `vzdump` → Synology NFS | PBS's own DR copy lives here (PBS excluded from its S3 job) |
| **Offsite** (3rd copy) | continuous | SeaweedFS `filer.backup` → Contabo S3 (`/buckets`) | `seaweedfs-backup.service` active |

Guest images capture everything on the rootfs and named docker volumes.
**Not captured by vzdump**: bind-mounts (`/data` on seaweedfs) — see below.

## Backup classes

- **A · guest-image** — state lives on the guest (volume/rootfs); PBS+NFS suffice.
- **B · app-consistent dump** — the app writes its own consistent dump on-guest
  before PBS runs (DB dumps, mail snapshots); PBS carries the dump.
- **C · object store** — state is in SeaweedFS S3; protected by the offsite sync.
- **D · code** — state is Ansible/catalog; rebuild = re-run the play.
- **E · ephemeral by design** — cache/scratch; no backup, rebuilds itself.

## Per-service matrix

| Service | Class | What is stateful · where | Mechanism | Restore |
|---|---|---|---|---|
| **postgresql** (cluster, 8 svc DBs) | **B** | `postgres:17` volume | `pg-backup` cron **02:00** → `pg_dumpall` → `/var/lib/postgresql/backups/all-DATE.sql.gz` (in guest → PBS) | `psql -U postgres < all-DATE.sql` on a restored/fresh guest; per-DB via `pg_restore` |
| **vault** | **B** | raft data volume | `vault_backup`: raft snapshot **02:15** → `/var/lib/vault/snapshots` (14 kept) + NFS + S3 | `vault operator raft snapshot restore` — **needs unseal keys** (print-kit); see `roles/vault_backup/README.md` |
| **mailcow** | **B** | vmail, MariaDB, redis, conf | `mailcow-backup.timer` **01:00** → helper `backup all` → `/var/backups/mailcow` (→ PBS 01:30); control-node cron **03:30** `--tags backup` → SeaweedFS `mailcow-backups` (Vault key) → Contabo; 7-day retention local + S3 | `helper-scripts/backup_and_restore.sh restore` |
| **gitlab** | **B + C** | PG DB (cluster), repos/uploads | `gitlab-backup create` cron → **S3** (`gitlab-backup-to-s3`); secrets in Vault `prod/gitlab/secrets`; `gitlab_archive`/restore role | `gitlab-backup restore` + Vault secrets; proven by the archive/restore role |
| **seaweedfs** | **C ⚠** | `/data` = ZFS `tank/data/seaweedfs` **bind-mount — NOT in vzdump** | offsite `filer.backup` → Contabo is the backup; ZFS dataset via `pve_zfs_mount` | restore from Contabo bucket sync; the guest itself is disposable (class D) |
| **harbor** | **A + C** | metadata in cluster PG; blobs on S3; `/data/harbor` = logs/trivy cache | PG dump (postgresql) + S3 offsite; local `/data/harbor` disposable | recreate guest (play) + PG restore; blobs already in S3 |
| **nextcloud** | **A + C** | DB in cluster PG; files on S3 primary; `nextcloud-app` volume (config) | PG dump + S3 offsite + volume in PBS | play + PG restore; `config.php` from volume/PBS |
| **netbox** | **A** | DB in cluster PG; `netbox-media` volume | PG dump + volume in PBS | play + PG restore |
| **authentik** | **A + D** | DB in cluster PG; media/templates volumes; blueprints = code | PG dump + volumes in PBS | play (blueprints re-render) + PG restore |
| **vaultwarden** | **A** | DB in cluster PG; `vaultwarden-data` (attachments/sends) | PG dump + volume in PBS | play + PG restore + volume |
| **jumpserver** | **A + C** | **bundled** PG+Redis named volumes; session recordings → S3 | volumes in PBS; recordings offsite | play + volume restore from PBS |
| **verdaccio** | **C** | packages + package db in SeaweedFS bucket `verdaccio` (identity in Vault `prod/verdaccio/s3`); `/opt/verdaccio/storage` = openid token store only | S3 offsite `filer.backup`; guest disposable (class D) | play (rebuilds image + config) — packages are already in S3 |
| **portainer** | **D** | `portainer-data` volume = console state only (environments, users, settings); agents stateless | PBS guest image (convenience); secrets in Vault `prod/portainer/*`; Authentik client in the blueprint | re-run the play (server, agents, environments and SSO are declared) |
| **jitsi** | **D** | none — stateless (no recordings); config + secrets regenerable | code (role) + Vault `prod/jitsi/secrets`; LXC in the guest jobs | redeploy `playbooks/jitsi.yml` |
| **step-ca** | **A ⚠** | `step-ca-data` volume (CA keys) | volume in PBS; CA password + root fingerprint in Vault | **volume + Vault password = the CA.** Lose both = re-init a new CA |
| **crowdsec** | **A** | LAPI sqlite (machines/bouncers) | PBS guest image; decisions ephemeral | play re-enrols agents/bouncers |
| **netbird** | **A** | mgmt store (`sqlite`) volume | PBS guest image | play + volume |
| **grafana** | **A + D** | dashboards/config as code; `grafana` DB in cluster PG | PG dump | play + PG restore |
| **prometheus / loki** | **E** | TSDB / WAL scratch (`/var/lib/loki` = cache only) | none — retention window, rebuilds | play |
| **redis** | **E** | cache only | none | play |
| **traefik / adguard / diagrams / warden / gitlab-runner** | **D** | config = Ansible/catalog | PBS guest image (convenience) | re-run the play |
| **pbs** | **A** | datastore is S3 (SeaweedFS) | **excluded from its own S3 job**; DR copy = NFS vzdump `vzdump-qemu-103` | restore VM from NFS; datastore re-attaches to S3 |
| **opnsense** | **A + D** | `/conf/config.xml` (auto-versioned in `/conf/backup`) | FW VM in PBS/NFS jobs; catalog = code; **nightly `config.xml` export** (`opnsense_config_backup` on the PVE host, 02:45): age-encrypted → NFS `dump-fw-config/` (30 daily / 12 monthly), key in Vault `prod/opnsense/config-backup-age` | restore VM, or seed-ISO rebuild from the catalog + seed; the export is the evidence/reference copy (decrypt drill ✓ 2026-09-04) |

## Restore drills (INF-44 — ≥1 per tier per year)

| Date | Drill | Result |
|---|---|---|
| 2026-09-04 | FW config export decrypt (`age -d` with the Vault key → `<opnsense>` root present) | ✓ |
| 2026-09-02 | PBS file restore from encrypted `ct/501/2026-09-02T01:32:06Z` (`pct.conf`) | ✓ content verified |
| 2026-08 | GitLab archive → restore (role) | ✓ proven |
| 2026-08 | Vault raft snapshot restore procedure | documented (`roles/vault_backup/README.md`) — drill pending |

## Logs (INF-45)

`vzdump` run logs ship from the PVE host via promtail (`journal`, host label
`srv-proxmox-poc-01`) → Loki; PBS task logs on `vm-pbs-01`. Failed jobs also
email `tech-support@` (to be moved to `alerts@` — queued).
