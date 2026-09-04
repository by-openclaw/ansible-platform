# role: pve_zfs_mount

Creates a ZFS dataset on the PVE host and bind-mounts it into an LXC (e.g. `tank/data/seaweedfs` → `/data`). ⚠ bind-mounts are NOT in vzdump — plan the backup class (see `docs/backup.md`).
