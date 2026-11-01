# Platform baseline — what every host runs and how it works

Measured live on 2026-11-01 (read-only census). Covers the 41 Linux hosts of the inventory: 39 guests and 2 hypervisors. Not covered: the firewall, the 3 Windows guests the owner keeps stopped, and `br-pmox-04`, which is adopted but not yet in the inventory.

This page says what **is**. Re-measure before trusting it: a value here is a measurement on that date, not a guarantee.

## Logs

| Step | How | Measured |
|---|---|---|
| Container output | Docker `log-driver: journald`, no `json-file` on disk | 38 of 38 Docker hosts |
| Journal | persistent, `SystemMaxUse=1G`, `SystemKeepFree=2G`, `RuntimeMaxUse=128M`, `MaxRetentionSec=30day` | 41 of 41 |
| Log files | `logrotate.timer`, last run without failure | 41 of 41 |
| Shipping | promtail reads the journal and files, pushes to Loki | 41 of 41 active |
| Storage | Loki keeps its data in the SeaweedFS bucket `loki-data` | 8.7 GB |

Largest `/var/log`: `srv-proxmox-poc-01` 3.2 G, `vm-pbs-01` 2.0 G, `vm-mailcow-01` 1.4 G, `lxc-pgsql-01` 1.1 G.

## Disks

| Disk | LXC | VM |
|---|---|---|
| Root | guest root on the node's ZFS storage | first disk |
| Second disk: `/var/lib/docker` | ZFS mount point, `backup=1`, 33 guests | second disk, ext4, unit ordered by `RequiresMountsFor`, 4 guests |
| Large data | a ZFS dataset bind-mounted into the guest | not used |

Two datasets exist: `tank/data/gitlab` (100 G, on `lxc-gitlab-01`) and `tank/data/seaweedfs` (800 G, on `lxc-seaweedfs-01`). **vzdump does not capture a bind mount**: `docs/backup.md` says how each is protected.

`vm-k3s-01` and `vm-pbs-01` run no Docker, so they have no second disk.

Highest use: `/data` on `lxc-seaweedfs-01` 51 %, root of `vm-pbs-01` 61 %. Every other root is at 44 % or less, every other data disk at 34 % or less.

## Swap

Set per guest by the `swap` variable in `infra-terraform-proxmox`.

| Hosts | Swap |
|---|---|
| LXC default | 512 MB |
| PostgreSQL members | 4096 MB |
| Redis members | 1024 MB |
| GitLab, Vault members | 0 |
| `vm-adguard-01`, `vm-adguard-02` | 2047 MB |
| `vm-mailcow-01` | 1023 MB |
| `vm-pbs-01` | 4095 MB |
| `vm-gitlab-runner-01`, `vm-k3s-01` | 0 |
| `srv-proxmox-poc-01` | 8191 MB |
| `br-pmox-03` | 0 |

## Security baseline

| Control | Measured |
|---|---|
| SSH on port 22222, root login off, password login off | 41 of 41 |
| Accounts: the break-glass admin, `svc-ansible-<env>`, `svc-rune-<env>`, nothing else | 41 of 41 |
| fail2ban, unattended upgrades, no failed unit | 41 of 41 |
| Host firewall | ufw on 39 guests; the 2 hypervisors use the Proxmox firewall |
| Wazuh agent | 40 of 41 — **`vm-adguard-02` has none** |
| CrowdSec agent | all but `lxc-crowdsec-01` (it is the server), **`vm-adguard-02`** and **`br-pmox-03`** |
| auditd | VMs and hypervisors only: a container cannot run it |
| Time | chrony on VMs and hypervisors; a container uses the host's clock |

## Virtual addresses

**One VIP exists: the resolver** (`platform_resolver_vip4`), held by keepalived on `vm-adguard-01` and `vm-adguard-02` (`roles/keepalived`, ADR infra/0011). Nothing else uses a VIP today. Other services are reached through a single endpoint host, or through Traefik.

## Clusters

| Service | Shape | State on 2026-11-01 | What is still single |
|---|---|---|---|
| PostgreSQL 17 | Patroni, 3 members, etcd on the same 3 | leader, sync standby, replica, lag 0 | endpoint `dbproxy` (HAProxy) on `lxc-pgpool-01` |
| Redis | 2 data members, 3 Sentinels (the third on `lxc-pgpool-01`) | running | endpoint on `lxc-pgpool-01` |
| Vault | 3 raft members | 1 active, 2 standby, unsealed | the unsealer `lxc-warden-01` |
| Authentik | 2 servers and workers | running | the LDAP outpost, on `lxc-authentik-01` only; `lxc-traefik-01` in front |
| Resolver | 2 VMs and a VIP | running | none at this layer |
| SeaweedFS | **1 node, replication `000`** | one copy, on a ZFS mirror | everything |
| Traefik, GitLab, NetBox, Harbor, monitoring | single instance | running | everything |

**Every guest listed here runs on one hypervisor, `srv-proxmox-poc-01`.** A cluster of guests protects against a guest failing, not against that node failing.

## Storage map

| Where | What it holds |
|---|---|
| ZFS pool `tank` on `srv-proxmox-poc-01`, Proxmox storage `poc-data` | guest roots, Docker disks, the two datasets |
| SeaweedFS S3 on `lxc-seaweedfs-01` | `loki-data`, `gitlab-*`, `harbor-registry`, `mailcow-backups`, `jumpserver-replays`, `verdaccio`, `nextcloud-data-mirror` |
| Synology NAS over NFS, mounted **only on the hypervisor** | `poc-backup` (guest backups), `poc-iso` (images) |
| Contabo S3 | bucket `pbs-datastore` (PBS), `seaweedfs-offsite` (copy of SeaweedFS), `nextcloud-data` (Nextcloud primary storage) |

No guest mounts NFS. **Leftover:** SeaweedFS still holds 420 GB in `pbs-datastore`, last written 2026-10-24, from before PBS moved to Contabo. It is 98 % of what SeaweedFS stores and nothing writes to it.

## Backups

See `docs/backup.md`. Times are the hypervisor's local time, Europe/Brussels.

## Vault

The path rule is `security/0001`: `{tier}/{service}/{key}`, and `{tier}/{service}/{hostname}/{key}` per node. Measured on `prod/`: 200 documents, 44 outside the rule, 196 with no metadata, no generated register. The migration table of that ADR has not been run. Never rename a document by hand: copy, switch the readers, retire, through `roles/vault_tidy`.
