# nas_shares

A Proxmox node's backup share on the NAS (Synology DSM 7) and the NFS rule that lets that node, and
no other, mount it. The NAS copy is the hot backup copy of ADR infra/0008 (7 daily + 4 weekly,
written by the node's nightly job, `roles/pve_host`).

- **Catalog:** `platform_nas` (`inventories/prod/group_vars/all/nas.yml`): the NAS address, the
  Vault path of the automation account, the volume, one `node_backup_shares` entry per node (share
  name, description) and `node_nfs_rule` (read-write, root mapped to admin, asynchronous).
- **How:** every change goes through `by_systems.synology_dsm` (`synology_dsm_share`,
  `synology_dsm_nfs`), thin wrappers over lib-synology-dsm `ensure()` — fetch, diff, nothing when
  equal; `--check` is the lib's dry run. No DSM API call in this role, no change by hand on the NAS.
- **Where it runs:** on each Proxmox node (its `ansible_host` is the rule's client); the NAS calls are
  delegated to the controller. `roles/pve_host` includes this role before it mounts the share, and
  `playbooks/nas.yml` runs it alone.
- **One share per node:** nodes that are not clustered can use the same VMID, and each node's job
  prunes by VMID; a shared folder would let one node prune the other's backups.
- **Credentials:** Vault only (`platform_nas.vault_path`), read at run time, `no_log`.

| ISO/IEC 27001:2022 | NIS2 Art. 21(2) | How |
|---|---|---|
| A.8.13 Information backup | (c) backup management | the node's hot backup copy has its own share |
| A.5.15 / A.8.3 Access control, restriction | (i) access control | the NFS rule admits the node's address only |
| A.8.9 Configuration management | (e) security in maintenance | the share and the rule are declared, converged, dry-runnable |
| A.5.17 Authentication information | (i) | the NAS account lives in Vault, never in the repository |
