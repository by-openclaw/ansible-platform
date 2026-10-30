# pve_host

The Proxmox VE hypervisor as code: from a bare Proxmox install to a platform node with one play
(`playbooks/pve-host.yml`). Apt sources (deb822, no-subscription), datacenter options, the Proxmox
firewall (IP sets from the inventory: management networks, admin desks, Traefik, bastion, monitoring;
default DROP; connectivity guard with automatic roll-back), the local admin `<org>@pam`, the OIDC realm
whose client `roles/authentik` mints into Vault, declared ACLs, and the UI route `proxmox.<domain>`
through Traefik. Exporters and agents come from their own plays (node group added to their targets);
hardening runs with `hardening_ufw_enabled: false` on nodes. Audit rows NODE-01…04.

Backups: the NAS job is declared and converged (`pve_host_nfs_backup_job`); node-wide, `/etc/vzdump.conf`
carries backup fleecing (PVE Admin Guide, "VM Backup Fleecing") so guest writes never wait on the backup
target — the fleecing storage is a per-node host var (`pve_host_vzdump_fleecing_storage`: a local,
thin-provisioned storage with discard; the play fails when it is missing or inactive). ISO 27001:2022
A.8.13 information backup, A.8.14 redundancy of information processing facilities, A.8.9 configuration
management.
