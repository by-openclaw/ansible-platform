# role: cerebrum_server

The EVS Cerebrum server application on its own Windows guest (`docs/services/cerebrum/playbooks.md` seq 2). The database is `roles/cerebrum_db`'s, the settings rows are `playbooks/cerebrum-db-config.yml`'s, the configuration (`.ccf`) is `playbooks/cerebrum-ops.yml`'s.

## Two layouts

- **Standalone** (`cerebrum_server_sql_bundled: true`): the installer's own SQL Server Express on this host (`/InstallSQL=Install`), then `roles/cerebrum_db` takes the instance over (Vault's `sa`, static port, logins, backup); the ini points at `localhost`.
- **Multi-VM** (default): `/InstallSQL=Skip`, the database on the `cerebrum_db` host.

## What it does, in order

1. Refuses to run without the Cerebrum installer and the WebView2 runtime pinned by sha256 on the object store, and without a `cerebrum_db` host; downloads and verifies both.
2. Installs the WebView2 runtime (the installer's dependency), then Cerebrum with the declared components (`cerebrum`, `cerebrum_watchdog` by default; the Designer where the inventory says so), silently, without the bundled SQL; the Sentinel driver only when `cerebrum_server_sentinel: install` (a hardware key).
3. A dedicated local account (`cerebrum`, password in Vault, created on first contact) whose logon starts the Watchdog and the server, the vendor's own way: both are desktop applications. It sits in `Administrators` because the vendor requires the application elevated for TLS on the web client; without TLS the inventory can lower it.
4. `Cerebrum.ini` as the vendor writes it (UTF-16): the database on the `cerebrum_db` host, instance and static port, the application login from Vault (written by `roles/cerebrum_db`), the bind addresses, no demo key on a licensed server; the file readable by Administrators, SYSTEM and the run account only.
5. Device definition files kept to the declared families plus the server's own (every `.cgd` loads, vendor checklist row 7); no pruning until the list is declared.
6. The site's project file from the object store when named.
7. The logon task: Watchdog then server, highest rights, one instance.
8. The firewall rules of the application, per port and bound to `Cerebrum.exe`: clients and panels on 40001/40002, the Northbound API on 40009 from the monitoring host and management, ACP and traps from the device ranges, the SNMP agent from the monitoring host; outbound to the database and the devices. A rule without a declared source stays present but disabled.
9. Error logs older than the retention removed.
10. With `cerebrum_server_start: true`: the logon task run once and the server port awaited (Cerebrum then creates its database and default settings).

## Not in this role

Accounts inside Cerebrum (`USERS.XML` holds hashed passwords; the vendor's procedure applies), the web client and its certificate (`roles/cerebrum_web`), the registry (`roles/cerebrum_nmos`), shipping the audit trail (a `windows_logging` file source, next), the auto-logon of the run account: a Windows session must exist for a desktop application; the platform does not store a logon password in the registry, so the session is opened at boot by the vendor's recommended means (an LSA-stored auto-logon set once by the operator) or stays an operator's RDP session. Decision pending with the vendor.

## Controls

| Control | Where |
|---|---|
| NIS2 Art. 21(2)(d), (e) | pinned installers from the platform's own store, checksum verified, declared components only |
| NIS2 Art. 21(2)(i), (j) | the application's own database login from Vault; the ini readable by three principals; a dedicated run account |
| ISO 27001 A.8.9 | every setting a variable; drift corrected on each run |
| ISO 27001 A.8.20 | per-port rules bound to the program; nothing program-wide |
| ISO 27001 A.8.15 | error-log retention |
