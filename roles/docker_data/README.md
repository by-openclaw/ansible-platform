# role: docker_data

Puts the Docker data root (`/var/lib/docker`) on its own volume on every Docker host — CIS Docker Benchmark 1.1.1 (separate partition for containers); ISO 27001:2022 A.8.6, A.8.13.

- **LXC:** a storage-managed mount point (`pct set -mpN <storage>:<GiB>,mp=/var/lib/docker,backup=1`) created on the guest's node, on the storage that holds its rootfs. The mount point is a volume, so vzdump includes it (a bind mount would not). The data is copied node-side between the two datasets while the engine is stopped; if the node does not hotplug the mount point into the running guest, the container is restarted once.
- **VM:** the second disk the Terraform module attaches (`vm-linux` `data_disk_size_gib`, scsi1) is formatted (ext4), the data copied, the volume mounted through fstab, and `docker.service` gains `RequiresMountsFor=/var/lib/docker` (systemd.unit(5)) so the engine never starts on the root filesystem again.

Idempotent: a guest whose data root is already a mount point is left alone. One engine stop per guest: run the play serial, one service at a time, and announce it.

Size: `docker_data_size_gib` (default 8 = 3× the largest use measured under 1.5 GB on 2026-10-31); larger hosts override in `host_vars` with the measured value as the comment.

```
ansible-playbook playbooks/docker-data.yml --check --limit <guest>   # plan only
ansible-playbook playbooks/docker-data.yml --limit <guest>           # one guest
ansible-playbook playbooks/docker-data.yml                           # fleet, serial 1
```
