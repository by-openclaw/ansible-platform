# role: cerebrum_db

The SQL Server instance EVS Cerebrum stores its state in. Cerebrum creates its own database at first start through the login its ini names (`docs/services/cerebrum/README.md` §15.2); this role owns everything around it.

## What it does, in order

1. Refuses to run unless the three installers are named on the object store with their sha256 (`cerebrum_db_installer_*`, `cerebrum_db_odbc_msi_*`, `cerebrum_db_sqlcmd_msi_*`), then downloads and verifies them.
2. `sa` password and the logins' passwords: Vault, created on first contact (`<tier>/cerebrum/<host>/sa`, `/app-login`, `/audit-ro`).
3. Installs SQL Server Express unattended, once: the answer file carries the `sa` password, is readable by Administrators and SYSTEM only, and is removed in the same play. `BUILTIN\Administrators` is the sysadmin account: the platform's SSH session manages the instance over Windows authentication, no password on a command line.
4. Installs the ODBC driver and `sqlcmd`.
5. A static TCP port on every address, dynamic ports off, Browser, Agent and telemetry off; the instance restarted only when its network settings changed.
6. Logins through a rendered SQL file (removed in the same play): the application login (`dbcreator` until its database exists, `db_owner` inside it), the audit login (`db_datareader`), SYSTEM for the backup task (`db_backupoperator`); `sa` takes Vault's password and is **disabled** (CIS 2.14) unless `cerebrum_db_sa_enabled: true`. Every statement is guarded, so a second run changes nothing.
7. A nightly full backup with checksum and verify, seven rotating files under `cerebrum_db_backup_dir`, as a scheduled task run by SYSTEM; the guest backup carries the folder off the host.
8. One inbound firewall rule: the instance port from the `cerebrum_server` hosts only.

## Inputs the inventory sets

| Variable | Meaning |
|---|---|
| `cerebrum_db_installer_url` / `_sha256`, `cerebrum_db_odbc_msi_url` / `_sha256`, `cerebrum_db_sqlcmd_msi_url` / `_sha256` | the pinned installers on the object store |
| `cerebrum_db_version`, `cerebrum_db_instance`, `cerebrum_db_port` | the instance |
| `cerebrum_db_database` | the name Cerebrum will create (vendor default `Cerebrum`; the lab's is `Cortex`) |
| `cerebrum_db_sa_enabled` | keep `sa` usable (default false) |
| `cerebrum_db_backup_time`, `cerebrum_db_backup_dir` | the nightly backup |

## Verification

- `ansible-playbook playbooks/cerebrum-db.yml`, then again: `changed=0`.
- The report line: instance, port, logins, `sa` state, database present or not yet, backup, firewall sources.
- A backup file younger than 24 h once the database exists.
- Not done by this role: TLS on the instance (`ForceEncryption` with the platform certificate), the redundant pair (mirroring with a witness, or Always On). Both are the next steps of the same role.

## Controls

| Control | Where |
|---|---|
| NIS2 Art. 21(2)(d) supply chain, (e) secure acquisition | pinned installers, checksum verified, from the platform's own store |
| NIS2 Art. 21(2)(i) access control, (j) authentication | no vendor default password; `sa` disabled; one login per use with least privilege; management over Windows authentication |
| NIS2 Art. 21(2)(c) backup | nightly native backup, verified, in the guest backup |
| ISO 27001 A.8.9 configuration management | every setting a variable, drift corrected on each run |
| ISO 27001 A.8.20 network security | one static port, one source, the Browser off |
| CIS SQL Server 2019 2.x, 3.x | services off, `sa` disabled, no `BUILTIN\Users`, Windows authentication for administration |
