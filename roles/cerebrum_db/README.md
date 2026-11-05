# role: cerebrum_db

The SQL Server instance EVS Cerebrum stores its state in. Cerebrum creates its own database at first start through the login its ini names (`docs/services/cerebrum/README.md` §15.2); this role owns everything around it.

## Two layouts

- **Dedicated database host(s)** (`cerebrum_db_install_source: microsoft`, the default): the instance comes from Microsoft's own SQL Server Express media, pinned on the object store.
- **Standalone server** (`bundled`): the Cerebrum installer put its SQL Express on the server host (`roles/cerebrum_server` with `cerebrum_server_sql_bundled: true`); this role only takes the instance over. The vendor's documented `sa` password is replaced by Vault's at the first run.

## What it does, in order

1. Dedicated host: refuses to run unless the media and the command-line utilities are pinned with their sha256 (`cerebrum_db_installer_*`, `cerebrum_db_sqlcmd_msi_*`), then downloads and verifies them. The media may come from a copy already on the host (`cerebrum_db_installer_staged_path`, a manual download), checked against the same sha256. Standalone: checks the bundled instance exists.
2. `sa` password and the logins' passwords: Vault, created on first contact, one folder per host and instance (`<tier>/mssql/<host>/<instance>/sa`, `/cerebrum_<n>`, `/cerebrum_federated`, `/jumpserver_editor`). `cerebrum_db_sa_vault_copy_from` gives `sa` the password of an existing document on first contact (a manual install).
3. Installs SQL Server Express unattended, once (telemetry off from the start), and restarts Windows when setup asks for it: the answer file carries the `sa` password, is readable by Administrators and SYSTEM only, and is removed in the same play. `BUILTIN\Administrators` is the sysadmin account: the platform's SSH session manages the instance over Windows authentication, no password on a command line.
4. Installs `sqlcmd` (Command Line Utilities 17, on the ODBC Driver 18 that SQL Server 2025 setup brings). Management connections pass `-C`: the instance has only its self-signed certificate until the platform's.
5. A static TCP port on every address, dynamic ports off, Browser, Agent and telemetry off; the instance restarted only when its network settings changed.
6. Logins through a rendered SQL file (removed in the same play): one login per Cerebrum instance, `cerebrum_<n>` from each `cerebrum_server` host's `cerebrum_instance`, with `sysadmin` (the owner's decision, 2026-11-03: the rights of `sa`, which the vendor uses by default); `cerebrum_federated` (sysadmin, for the Federation service); `jumpserver_editor` (`db_datareader` + `db_datawriter` in every Cerebrum database, for browsing through the bastion); the logins other platform services declare (`cerebrum_db_logins_platform`, the inventory: the DbGate views' `dbgate_admin`, `dbgate_cerebrum_<n>`), with their roles inside their own `databases` only, no server role (a database that does not exist yet, the Federation one, is granted at the first run after it does); SYSTEM for the backup task (`db_backupoperator`). `sa` takes Vault's password and is **disabled** (CIS 2.14) unless `cerebrum_db_sa_enabled: true`. Every statement is guarded, so a second run changes nothing; a database Cerebrum has not created yet is reported, not an error.
7. A nightly full backup of every Cerebrum database (`Cerebrum_<n>`) with checksum and verify, seven rotating files each under `cerebrum_db_backup_dir`, as a scheduled task run by SYSTEM; the guest backup carries the folder off the host.
8. One inbound firewall rule per instance: its port, bound to its `sqlservr.exe`, from the `cerebrum_server` hosts and the platform logins' `from` addresses (the DbGate host) only.

## State, upgrades, patches

- `cerebrum_db_state: present | absent`. Absent uninstalls the instance with Microsoft's media and removes the backup task and the firewall rule; the data files, the backups and the Vault documents stay.
- `cerebrum_db_patches`: Microsoft's GDR/CU packages, pinned (kb, version, url, sha256), applied in order when the instance's patch level is below them; the instance restarts with the patch. A major upgrade (2019 → 2022) is a new `cerebrum_db_version` with its media: the vendor's supported SQL versions decide when.
- `cerebrum_db_hardening`: CIS SQL Server 2019 section 2 server options as declared data (`cerebrum_db_sp_configure`), login auditing (`cerebrum_db_audit_level`, both outcomes), `sa` disabled; `BUILTIN\Administrators` stays the management door of this dedicated host, the documented exception.
- The vendor bundle (`cerebrum_db_install_source: bundled`) exists for a server that already carries it; the platform does not use it: no Microsoft patch channel.

## Inputs the inventory sets

| Variable | Meaning |
|---|---|
| `cerebrum_db_installer_url` / `_sha256` / `_staged_path`, `cerebrum_db_sqlcmd_msi_url` / `_sha256` | the pinned installers |
| `cerebrum_db_version`, `cerebrum_db_instance`, `cerebrum_db_port` | the instance |
| `cerebrum_instance` (on each `cerebrum_server` host) | the instance number: database `Cerebrum_<n>`, login `cerebrum_<n>` |
| `cerebrum_db_sa_enabled`, `cerebrum_db_sa_vault_copy_from` | keep `sa` usable (default false); where its first password comes from |
| `cerebrum_db_backup_time`, `cerebrum_db_backup_dir` | the nightly backup |

## Verification

- `ansible-playbook playbooks/cerebrum.yml`, then again: `changed=0`. A dry run before the first install stops at the install: there is no instance yet to configure.
- The report line: instance, port, logins, `sa` state, the databases Cerebrum has not created yet, backup, firewall sources.
- A backup file younger than 24 h once the database exists.
- Not done by this role: TLS on the instance (`ForceEncryption` with the platform certificate), the redundant pair (mirroring with a witness, or Always On). Both are the next steps of the same role.

## Controls

| Control | Where |
|---|---|
| NIS2 Art. 21(2)(d) supply chain, (e) secure acquisition | pinned installers, checksum verified, from the platform's own store |
| NIS2 Art. 21(2)(i) access control, (j) authentication | no vendor default password; `sa` disabled once the instances use their own logins; one login per Cerebrum instance (sysadmin: the owner's documented exception, as the vendor's `sa`), the bastion's editor with data rights only; management over Windows authentication |
| NIS2 Art. 21(2)(c) backup | nightly native backup, verified, in the guest backup |
| ISO 27001 A.8.9 configuration management | every setting a variable, drift corrected on each run |
| ISO 27001 A.8.20 network security | one static port, one source, the Browser off |
| CIS SQL Server 2019 2.x, 3.x | services off, `sa` disabled, no `BUILTIN\Users`, Windows authentication for administration |
