# role: opnsense_config_backup

Nightly export of the firewall's `config.xml` (issue #13 · ISO27001 A.8.13 / A.5.30, NIS2 Art.21(2)(c)). Runs on the **PVE host** (has the Synology share mounted at `/mnt/pve/poc-backup` and reaches the FW over OOB): `GET /api/core/backup/download/this` (strict TLS via `--resolve fw.<domain>`) → **age**-encrypted → `dump-fw-config/daily/fw-config-<date>.xml.age` (+ `monthly/` on the 1st). Retention 30 daily / 12 monthly.

- Keys: the age keypair is get-or-created in Vault `prod/opnsense/config-backup-age` (`public_key`, `private_key`); only the **recipient** (public key) is on the host. FW API creds come from the `opnsense` group vars (Vault-native) into a root-0600 env file.
- **Backup only.** Restore = seed-ISO reinstall (services/0001), never a live `config.xml` push.
- Schedule: `opnsense-config-backup.timer` 02:45 (+≤5 min jitter). Run once: `systemctl start opnsense-config-backup.service`.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/opnsense-config-backup.yml`

## Backup & restore

This role *is* the backup (class **D** for the FW config; the FW VM itself is class A in PBS/NFS). Restore drill: `age -d -i <private key from Vault> fw-config-<date>.xml.age` → import via the seed pipeline. Matrix: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `systemctl list-timers opnsense-config-backup*`; `ls -l /mnt/pve/poc-backup/dump-fw-config/daily | tail -3`; `journalctl -u opnsense-config-backup -n 5`.
- Decrypt test (evidence for A.8.13): fetch the private key from Vault to a 0600 tmp file, `age -d -i key.txt file.age | grep -c '<opnsense>'`, shred the tmp file.
- Common: `not an OPNsense config` → API creds/URL; `RequiresMountsFor` failure → NFS share not mounted on the PVE host.
