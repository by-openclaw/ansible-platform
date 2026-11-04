# EVS Cerebrum — install, runbook, settings

The Cerebrum platform in the dev tier: one SQL Server instance, two Cerebrum servers (instances 01 and
02), each with its Client, Designer, Service Manager and Federation components. Everything below is
measured on the live guests (2026-11-03/04) or set by the roles named; vendor references are the
Cerebrum User Manual issue 2.9 (August 2026) and the 2.9.3 release notes.

Status legend: **done** (applied and proven), **pending** (decided, not built), **later** (kept out on
purpose until its decision), **manual** (a hand step, said why).

## 1. Layout

| Host | IP | Role | Inventory group | Instance |
|---|---|---|---|---|
| `vm-winsql-01` | 10.6.239.203 | SQL Server 2025 Express, instance `BY_CEREBRUM` | `cerebrum_db` | — |
| `vm-winapp-01` | 10.6.239.201 | Cerebrum server + Client + Designer | `cerebrum_server` | `01` |
| `vm-winapp-02` | 10.6.239.202 | Cerebrum server + Client + Designer | `cerebrum_server` | `02` |

All three: Windows Server 2025 (owner's choice; the manual lists 2019/2022, the install was done with
EVS), on `br-pmox-03`, bridge `vmbr0`, VLAN 600 (`MGMT_CTRL`, 10.6.224.0/20). People reach them through
JumpServer (RDP). Each instance has its own database (`Cerebrum_<n>`) and SQL login (`cerebrum_<n>`).

## 2. What is automated, what is not

| Part | How | State |
|---|---|---|
| SQL instance, logins, backup, CIS options, firewall | `roles/cerebrum_db` | done |
| ODBC Driver 17 on the Cerebrum servers | `roles/mssql_odbc` | done |
| Cerebrum firewall rules (bound to `Cerebrum.exe`) | `roles/cerebrum_server` `firewall.yml` | done |
| Sentinel RMS persistence (licence prerequisite) | `roles/cerebrum_server` `sentinel.yml` | done |
| `Cerebrum.ini` SQL lines | `roles/cerebrum_server` `ini.yml` | done |
| Settings (`_Config` rows), the applied set | `roles/cerebrum_server` `config.yml` | done |
| RCP address reservations (8080 `/v1`, `/v2`) | `roles/cerebrum_server` `http_reservations.yml` | done |
| NMOS registry host: Bonjour, reservations and firewall on 8090 | `roles/cerebrum_nmos`, `playbooks/cerebrum-nmos.yml` | done |
| NMOS registry itself (device service `nmos-registry-<n>`, "Network Media Server" device, port 8090) | Cerebrum (`.ccf`) | **manual** |
| Admin password in Vault, encrypted forms captured | `roles/cerebrum_server` `admin_password.yml`, `admin_capture.yml` | done |
| Cerebrum installer (components, Sentinel) | the vendor's installer | **manual** (done with EVS); the role's unattended install exists, its pins are pending (installer store) |
| SQL password in the SQL tab, Admin password at first start | the Cerebrum UI | **manual, once per new instance**: Cerebrum stores both encrypted with an unpublished method (§9) |
| Trial licence key | EVS support | **manual**: public key → EVS → key number |
| System configuration (devices, control interfaces, routes, users, groups) | `.ccf` / `_SystemConfig` | **manual** for now (§8) |
| Split DNS names | AdGuard | pending |
| Certificates (web client, RCP) | lego (Let's Encrypt) → Vault → role | pending |
| JumpServer: SQL instance as a database asset | `roles/jumpserver` | pending |
| C-Link multicast group | `_Config` rows | pending: range to confirm with EVS |
| Windows base (route, accounts, CIS L1, logging) | `playbooks/windows-guests.yml` | pending: not applied to these guests yet (§10) |

## 2a. Compliance with EVS's recommendations

For EVS to check each point against its own manual (Cerebrum User Manual issue 2.9, §3.1–3.6, and the
"NMOS IS-04-5 Help"). **Now** = measured on vm-winapp-01 on 2026-11-04 (vm-winapp-02 is built the same
way); **Check** = where anyone can verify it.

| § | EVS recommendation | Now | Status | Check |
|---|---|---|---|---|
| 3.1 | OS: Windows Server 2019 / 2022 | Windows Server 2025 Standard **Evaluation** (build 26100) | deviation, accepted with EVS at install; the evaluation edition must be licensed | `winver` |
| 3.1 | SQL: non-redundant ≥ 2017 Express | SQL Server 2025 Express 17.0.1000.7 (remote, vm-winsql-01) | ok | SSMS / `SELECT @@VERSION` |
| 3.1 | RAM ≥ 16 GB | 32 GB | ok | Task Manager |
| 3.1 | CPU ≥ dual core; 4 cores recommended | 6 vCPU | ok | Task Manager |
| 3.1 | Disk ≥ 160 GB | 120 GB virtual disk, **C: 79 GB** | **gap** | Disk Management |
| 3.1 | Two Ethernet ports | one (VirtIO 10 Gb/s) | gap (dev) | `ncpa.cpl` |
| 3.1 | .NET Framework 3.5 SP1 or later | 4.8 built in; 3.5 feature removed | ok ("or later") | `Get-WindowsFeature NET-Framework-Core` |
| 3.1 | Sentinel licensing | Sentinel driver 7.6.1 + RMS persistence initialised | ok | Help → About |
| 3.2 | Dedicated CPU / memory, pinning or low latency | 6 cores pinned (affinity), NUMA-bound to one node, memory not shared | ok | Proxmox `qm config` (affinity, numa0 policy=bind) |
| 3.2/3.5 | Thick-provisioned disks | ZFS volume, thin (no reservation) | **gap** | `zfs get refreservation` |
| 3.3 | SQL: read/write on the application tables, read on the system views | login `cerebrum_<n>` = sysadmin | ok | §4 |
| 3.3 | Database files not compressed | SQL data on NTFS, compression off | ok | file properties |
| 3.4 | Install as administrator | done with EVS | ok | |
| 3.4 | Firewall lets Cerebrum's traffic in | explicit rules bound to `Cerebrum.exe` (§9.1) | ok | `wf.msc` → CEREBRUM-* |
| 3.4 | Client logon: Multicast / Unicast / TCP | TCP for the test; multicast once its group is set | pending | Client Log On |
| 3.5 | UAC: Never Notify | **Always notify** (`ConsentPromptBehaviorAdmin` 2) | **gap**: Cerebrum runs unelevated (RCP needed reservations) | `UserAccountControlSettings` |
| 3.5 | Power: High Performance | High performance | ok | `powercfg /getactivescheme` |
| 3.5 | Visual effects: best performance | not set | gap (cosmetic) | System Properties |
| 3.5 | Firewall off, or explicit permits | on, explicit permits | ok | §9.1 |
| 3.5 | NIC power management off | not supported by the VirtIO adapter | n/a | Device Manager |
| 3.5 | Anti-virus: exclude Cerebrum processes and folders | Defender on, **no exclusion** | **gap** | `Get-MpPreference` |
| 3.5 | Run Cerebrum and Watchdog as administrator | not set | **gap** | file properties → Compatibility |
| 3.5 | Startup folder: Cerebrum, Watchdog, Witness | empty; Watchdog not running | **gap** | `shell:startup` |
| 3.5 | Hosts file entries on every Cerebrum server | none | **gap** | `C:\Windows\System32\drivers\etc\hosts` |
| 3.5 | Explorer: extensions and hidden files shown | not set | gap (cosmetic) | Explorer options |
| 3.6 | Service Manager installed (`ServiceInstall.bat`) | `CerebrumServiceManager` Running / Automatic | ok | `services.msc` |
| NMOS | Bonjour for Windows | Bonjour 2.0.2, service Running / Automatic | ok | `services.msc`, `dns-sd` |
| NMOS | Registry URL reservations (`netsh http add urlacl`) | `http://*:8090/x-nmos/registration/` and `/x-nmos/query/` | ok (port 8090, §9.1) | `netsh http show urlacl` |
| NMOS | Registry port open in the firewall | `CEREBRUM-In-NMOS-Registry` TCP 8090 | ok | `wf.msc` |

The gaps marked **gap** are the Windows deployment step (§12): UAC, Defender exclusions, run as
administrator, start-up, hosts file — each set by a role, each a recorded exception to the platform's
CIS baseline where it conflicts.

## 3. Runbook

Run from the repository root, key agent loaded (`SSH_AUTH_SOCK=~/.ssh/rune-agent.sock`). Every play:
dry run first (`--check --diff`), then apply, then apply again: the second run must say `changed=0`.

### 3.1 SQL Server (`vm-winsql-01`)

```
ansible-playbook playbooks/cerebrum.yml --limit vm-winsql-01 --check --diff
ansible-playbook playbooks/cerebrum.yml --limit vm-winsql-01
```

- A first install may restart `vm-winsql-01` twice (a pending restart before setup, setup's own 3010).
  Announce it first.
- Report line to read: instance, port, logins, `sa` state, the databases Cerebrum has not created yet,
  backup, firewall sources.
- Removing an instance (data files kept): `-e cerebrum_db_state=absent -e cerebrum_db_instance=<NAME>
  -e cerebrum_db_features=<FEATURES>`; a restart follows before the next install.

### 3.2 Cerebrum servers (`vm-winapp-01`, `vm-winapp-02`)

```
ansible-playbook playbooks/cerebrum.yml --limit vm-winapp-01,vm-winapp-02 --check --diff
ansible-playbook playbooks/cerebrum.yml --limit vm-winapp-01,vm-winapp-02
```

In order: ODBC driver → firewall → Sentinel → `Cerebrum.ini` → settings rows → Admin password in Vault →
capture of the encrypted forms. No restart by Ansible; Cerebrum reads the ini and the rows at start, so
**restart Cerebrum** after a run that changed them.

### 3.2a NMOS registry hosts

```
ansible-playbook playbooks/cerebrum-nmos.yml --check --diff
ansible-playbook playbooks/cerebrum-nmos.yml
```

Bonjour (Apple, pinned, signature checked), the 8090 reservations, the firewall rule. Then in Cerebrum:
Cerebrum device → 02:Services → add the Service Manager → Create New Service `nmos-registry-<n>` (and
`third-party-<n>`); on `nmos-registry-<n>` add the "Network Media Server" device (NMOS IS-04/5) with port
**8090**. Check: `http://127.0.0.1:8090/x-nmos/registration` lists the versions; every node is registered
by hand with its registry's address (no mDNS / DNS-SD).

### 3.3 First start of a new instance (manual, once)

1. Start Cerebrum. Open Configuration → **SQL**: the connection, database and user are already filled in
   by the ini. In **Password**: Ctrl+A, Delete, then paste the login's password from Vault
   `secret/dev/mssql/vm-winsql-01/BY_CEREBRUM/cerebrum_<n>`. **Test once** (expected: "Username/Password
   Correct", database does not exist yet), then Apply → OK. Five wrong passwords lock the login (§9).
2. Restart Cerebrum: it creates `Cerebrum_<n>` and asks for its Admin password: paste it from
   `secret/dev/cerebrum/<host>/app-admin`.
3. Run 3.2 again: it stores both encrypted forms in Vault (`ini_password_encrypted`,
   `password_encrypted`). From then on a rebuild of that instance needs no typing.

### 3.4 Licence (manual)

1. Sentinel must be initialised (3.2 does it; Help → About otherwise asks for `SentinelPersistanceInstall.bat`).
2. With Trial License Mode on (`GUI/DEMO_MODE_LOGON = 1`), Cerebrum shows its **public key** at start
   (instance 01: `111bf115`). Send it to support@evs.com.
3. Paste the key number EVS returns. Then it goes to Vault `secret/dev/cerebrum/<host>/license`
   (`public_key`, `key_number`) — pending: the role writing `License:Demonstration_Key` from there.

### 3.5 Client and Designer test

On each server, the Client logs on to the **other** server (srv1 → srv2 and back), then the Designer.
Values in §7.6. Proves the firewall, C-Link and the logins.

### 3.6 Rebuild of an existing instance

The playbook replays everything, including the two encrypted passwords captured in 3.3 (the ini line
from `ini_password_encrypted`; the Admin row of `_Users` from `password_encrypted`, EVS's own method —
the replay of the Admin row is pending, the capture is done). The `.ccf` restores the system
configuration (§8).

## 4. SQL Server — `roles/cerebrum_db` (done)

| Setting | Value | Why / where |
|---|---|---|
| Edition, version | SQL Server 2025 Express 17.0.1000.7 | manual §3.1: Express is enough for a non-redundant system; group_vars `cerebrum_db.yml` |
| Media | `SQLEXPR_x64_ENU.exe`, sha256 `74aa90c1…5297` | Microsoft ships 2025 Express only through its web installer; the copy it downloaded is staged on the host and verified (`cerebrum_db_installer_staged_path`) until the installer store holds it |
| Setup account | SYSTEM (runas, task variables) | setup protects settings with DPAPI, which a key-based SSH session cannot use |
| Instance | `BY_CEREBRUM` (ID `MSSQL17.BY_CEREBRUM`) | owner's name: letters, digits, `_`, 16 at most |
| Features | `SQLENGINE` only | no Full-text, no Machine Learning, no Agent |
| Collation | `French_CI_AS` (the guest's locale) | |
| Authentication | mixed (SQL logins for Cerebrum) | Cerebrum signs in with SQL logins |
| Network | TCP on, **static port 1433**, dynamic ports off, named pipes off | Cerebrum connects to `<ip>\BY_CEREBRUM,1433` |
| Services off | SQL Browser, Agent, Telemetry | CIS 2.x; the Browser is why the connection string carries `,1433` |
| sqlcmd | Command Line Utilities 17.0.4055.5 (ODBC 18) | management over Windows authentication, `-C` (self-signed certificate) |
| `sa` | Vault password, **disabled** | CIS 2.14; each instance has its own login |
| Logins | `cerebrum_01`, `cerebrum_02`, `cerebrum_federated` (sysadmin); `jumpserver_editor` (`db_datareader` + `db_datawriter` in every `Cerebrum_<n>`) | owner: instance logins have the rights of `sa`; a locked login is unlocked with the Vault password |
| Server options | CIS SQL 2019 §2 (`xp_cmdshell`, `clr`, `remote admin`, … = 0) | `cerebrum_db_sp_configure` |
| Login auditing | both success and failure (level 3) | CIS 5.1, NIS2 21(2)(b) |
| Databases | `Cerebrum_01`, `Cerebrum_02`: created by Cerebrum at first start; recovery model SIMPLE | the backup restores to last night (RPO 24 h in dev) |
| Backup | daily 02:00, SYSTEM, full + checksum + `RESTORE VERIFYONLY`, 7 files per database in `C:\Backup\SQL` | proven: `Cerebrum_01_Tuesday.bak` 6 MB, `Cerebrum_02_Tuesday.bak` 5.5 MB |
| Windows firewall | `CEREBRUM-DB-In-SQL-BY_CEREBRUM`: TCP 1433 bound to `sqlservr.exe`, from the Cerebrum servers only | JumpServer's source: pending |

## 5. Cerebrum server — install and Sentinel

| Setting | Value | Note |
|---|---|---|
| Version | 2.9.3 (build 15692, 16/10/2026), web client 2.9.3 b2222 | |
| Components installed | `cerebrum`, `cerebrum\cerebrum_watchdog`, `cerebrum_designer`, `cerebrum_client`, `cerebrum_service_manager`, `cerebrum_federation`, `gilze_clfs` (EVS Media Infrastructure Device UI's) | read from the installer's record (`Inno Setup: Selected Components`); not installed: `cerebrum_witness`, `cerebrum_database_mirror_creator`, `cerebrum_sdn` |
| Unattended switches | `/InstallSentinel=Install /InstallSQL=Skip /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /COMPONENTS=… /LOG=…` | EVS's own playbook; manual §3.4 `/HELP` |
| Sentinel driver | Sentinel System Driver Installer 7.6.1 | not on the SQL server |
| Sentinel RMS persistence | `Sentinel_Init.exe`, then marker `HKLM\SOFTWARE\WOW6432Node\EVS Broadcast Equipment\Cerebrum\Sentinel` `installed=1` | the vendor's `SentinelPersistanceInstall.bat` pauses and does not wait; the role waits and marks |
| ODBC | Driver 17 for SQL Server 17.11.1.1 | Cerebrum's SQL tester looks up 17, 13, 11, Native Client by name, not 18 |
| Start | manual today | pending: Cerebrum + Watchdog as administrator at sign-in (manual §3.5) |

## 6. `Cerebrum.ini` — `ini.yml` (done)

UTF-16, `C:\Program Files\EVS Broadcast Equipment\Cerebrum\Cerebrum.ini`; one line per declared key, the
other lines (Cerebrum's own) kept.

| Line | Value |
|---|---|
| `CORTEX:DISABLE_CRASH_DUMP` | 0 |
| `SQL:USE_DEFAULT` / `SQL:LOGIN_CREDENTIALS` | 0 / 2 (manual user and password) |
| `SQL:LOGIN_USERNAME` | `cerebrum_<n>` |
| `SQL:LOGIN_PASSWORD` | **encrypted by Cerebrum**; the role never writes the clear password, replays the captured one |
| `SQL:PRIMARY_CONNECTION` | `10.6.239.203\BY_CEREBRUM,1433` |
| `SQL:REDUNDANT` | 0 |
| `SQL:SECONDARY_CONNECTION` / `SQL:SECONDARY_DATABASE` | `localhost\CEREBRUMSQL` / `Cortex` (Cerebrum's own values on a non-redundant server) |
| `SQL:DATABASE` | `Cerebrum_<n>` |
| `SQL:USE_MULTI_SUBNET_CLUSTERING`, `IP:PRIMARY` | 0, 0 |
| `VIRTUAL:*_BIND_ADDRESS`, `COR_LINK:BIND_ADDRESS` | 0.0.0.0 (Cerebrum's defaults; set through `cerebrum_server_ini_settings_extra` when the media networks exist) |

## 7. Settings — `_Config` rows, `config.yml`

Rows `__General__ / CATEGORY / PROPERTY = value` of each instance's database, written only where they
differ; a dry run prints what would change. Cerebrum reads them at start.

### 7.1 Applied (done; inventory `group_vars/cerebrum_server.yml`)

| Tab | Rows |
|---|---|
| General | `CORTEX/ALLOW_VIRTUALISE` 1, `GUI/DEMO_MODE_LOGON` 1 (trial licence mode) |
| Tally & Router → View/Behaviour | `GUI/TALLYRTR_*_MNE_MODE` (RouteMaster, Joysticks, Cables & Tally, UMDs = IO Mnemonic 4294967295; Categories, Salvos = Default 0), `GUI/TALLYRTR_SALVO_ACTIONS` 0, `TALLY_ROUTER/CLEAR_UMDS_ON_DEACT` 0, `TALLY_ROUTER/SAVE_LOAD_UMD_STATE` 0, `GUI/RECALL_RTR_GRID_ENABLE` 0, `GUI/RECALL_TALLY_GRID_ENABLE` 0, `GUI/PREVENT_RESERVED_CHARS` 1 |
| Tally & Router → Backup | `TALLY_ROUTER/AUTO_BACKUP` 2 (daily), `BACKUP_TIME` 35520512 (02:30:00), `BACKUP_LIMIT` 1, `BACKUP_SIZE` 30, `BACKUP_DIRECTORY` `C:\Backup\Cerebrum`, `ALLOW_ROUTE_IMPORTS` 0 |
| Tally & Router → IPConfig | `IP_RTR/*`: device in label 1, BBM 0, audio channels 16, dynamic audio/video bandwidth 1/1, default bandwidth video/audio/data 3075/25/10, overhead 10/10, ignore disconnect 30 s, self-heal 1, forward SDP 1, sender label in SDP 1 |
| Tally & Router → Routemaster | `RC/ROUTEMASTER_*`: re-assert 0, update interval 500 ms, block partial 0, pending 0, lock sync 0, exact tag match 0 |
| Hosting | `RCP/ENABLE_RCP` 1 (plain for now) |

### 7.2 Mapped, kept for later (not declared)

| Tab | Rows | Waits for |
|---|---|---|
| Logging (syslog, mandatory) | `LOGGING/USE_LOGGING_SERVER`, `SERVER_1_ADDRESS/PORT`, `TRANSPORT_TYPE` (1 = TCP), `MESSAGES_TO_LOG` (2 = audit trail + event log), `USE_SSL` | a Loki listener for Cerebrum (RFC5424 TCP), a main-firewall rule; "Use Logging Server" is greyed until licensed |
| Hosting / Security | `WEB_CLIENT/ENABLED`, `USE_SSL`, `WEB_SERVER_PORT` (80 → 443), `PORT` 40002, `RCP/USE_SSL`, `RCP/HTTP_PORT` 8080, `SECURITY/CERTIFICATE`, `KEY`, `CERT_HASH` | split DNS name and certificate per instance; plain first, then TLS |
| C-Link | `COR_LINK/MULTICAST_ADDRESS`, `MULTICAST_PORT` 40001, `SERVER_NAME` ("Cerebrum Server" → "Cerebrum 01/02"), Enable Client Connections | the multicast range (EVS) |
| Project | `PROJECT/PROJECT_DIRECTORY_USE_CUSTOM`, `PROJECT_DIRECTORY` | the folder's format (Projects\<instance>, Common); Server and Designer both |
| SQL tab | `SQL/MAX_DB_*`, `*_ARCHIVING`, `ARCHIVE_DIRECTORY` (→ `C:\Backup\Cerebrum\SQL Archive`), `FORCE_TRUNCATE` | |
| SNMP, SNMP Traps | `SNMP/*` (agent communities `public`/`private`!), `TRAP/*` | hardening: own communities from Vault, SNMPv3, agent firewall rule |
| Email, Base SMTP | `EMAIL/*` | Cerebrum's own Mailcow mailbox (`mail/cerebrum`), 587 + TLS |
| Alarm, Audit | `ALARM/*`, `RC/LOG_*`, `AUDIT/*_LEVEL` (bit masks: Error 1, then 2, 4…) | |

## 8. Where Cerebrum keeps what (measured)

| What | Where | Managed by |
|---|---|---|
| SQL connection, bind addresses | `Cerebrum.ini` | `ini.yml` |
| Every Configuration tab | `_Config` rows | `config.yml` |
| Devices, control interfaces (e.g. **DHS**, Cerebrum XML), routes, macros, users, groups | `_SystemConfig`: one row of binary blocks = the `.ccf` | the `.ccf` (export / import, manual); its own daily backup (§7.1) |
| SQL password | `Cerebrum.ini`, encrypted | captured to Vault, replayed |
| Admin password | `_Users.PasswordEncrypt`, encrypted (97 characters, not a plain hash) | captured to Vault |
| Sentinel persistence | `C:\ProgramData\SafeNet Sentinel\…` + the vendor's marker | `sentinel.yml` |
| Registry | nothing of Cerebrum's settings | |

## 9. Firewall and network

### 9.1 Windows firewall on the Cerebrum servers — `firewall.yml` (done)

Default: block inbound. Every rule bound to `Cerebrum.exe`.

| Rule | State | Ports | From |
|---|---|---|---|
| `CEREBRUM-In-Server-TCP` / `-UDP` | on | 40001–40005 (C-Link: multicast/TCP, client and Designer unicast) | 10.6.224.0/20 (OOB), 10.6.240.0/20 (fabric) |
| `CEREBRUM-In-Northbound` | on | 40007 (Cerebrum XML: **DHS**) | monitoring host, the same networks; to narrow to the DHS host |
| `CEREBRUM-In-SNMP-Agent` | off | 1161 | until the SNMP agent is hardened |
| `CEREBRUM-In-ACP`, `-SNMP-Traps`, `-Out-ACP` | off | 2071–2072, 162 | until the device networks are declared |
| `CEREBRUM-Out-SQL` | on | → 10.6.239.203:1433 | |
| `CEREBRUM-In-RCP` | on | 8080 (HTTP), 8081 (WebSocket): RCP | monitoring host, management networks; to narrow to the DHS host |
| `CEREBRUM-In-NMOS-Registry` (`roles/cerebrum_nmos`) | on | 8090: NMOS IS-04/05 registry | management networks (device networks once declared) |
| Web client (443) | pending | | with TLS |

HTTP.sys reservations (Everyone by SID `D:(A;;GA;;;WD)`, listen + delegate, as EVS asks): RCP
`http://*:8080/v1/`, `/v2/` (Cerebrum asked for them in its log: it runs unelevated); NMOS
`http://*:8090/x-nmos/registration/`, `/x-nmos/query/`.

**Ports on a Cerebrum server** (owner, 2026-11-04): C-Link 40001–40005, Northbound (DHS) 40007, RCP
8080/8081, NMOS registry **8090** (not EVS's example 8080: RCP keeps 8080 on the same server and no NMOS
specification fixes the registry's port), SNMP agent 1161 (closed).

### 9.2 Network and multicast

- VLAN 600 on both fabric switches: IGMP snooping with pruning, **querier 10.6.255.252** (fabric-1;
  fabric-2 10.6.255.253 standby), fast-leave; layer 2 only, no PIM. Bridge `vmbr0` on `br-pmox-03`:
  snooping on, no querier of its own (the switches query).
- The fabric's multicast plan (switch configuration): `239.0.0.0/16` **never** (MAC aliases of
  224.0.0.x/224.0.1.x); `239.1–63` RED ST 2110 plane; `239.64–127` BLUE plane.
- Cerebrum C-Link group: proposed from the organisation-local range `239.192.0.0/14` (RFC 2365),
  `239.192.10.1` = instance 01, `239.192.10.2` = 02 — **to confirm with EVS**. One group per instance:
  both share the VLAN.
- Clients through JumpServer run on a server in the VLAN: multicast works. Through the VPN (WireGuard):
  unicast only.
- Cerebrum listens on TCP/UDP 40001, UDP 40002, TCP 40007, UDP 1161 (all addresses).

### 9.3 Names and certificates — pending

- **Split DNS**: `cerebrum-01.dev.<platform_domain>` → .201, `cerebrum-02.dev…` → .202,
  `cerebrum-db.dev…` → .203, answered by the platform resolver (AdGuard) only, never published.
- **Certificates**: one per instance name, Let's Encrypt via `roles/lego_cert` (Cloudflare DNS-01) on a
  platform Linux host, handed over through Vault (the Cloudflare token never reaches a Windows guest);
  the role writes the `.crt`/`.key` to a folder Administrators and SYSTEM only, imports into the machine
  store, sets `SECURITY/CERTIFICATE`, `KEY`, `CERT_HASH`. No certificate is installed today (the rows name
  EVS's default files, which do not exist).

## 10. Client, Designer, users, access

### 10.1 Client logon (Cerebrum Client)

| Field | Value |
|---|---|
| Cerebrum | Use TCP for now (multicast once the group is set; VPN clients: unicast) |
| Server address | the other server's IP (the field takes an IP, not a name) |
| Enable Redundancy | off |
| Logon License | Full |
| Options | System Configuration on, Alarm Log Updates on |
| Logon Method | Standard |
| User / Password | a Cerebrum user (Admin for the test, from `app-admin`) |
| Remember credentials and auto-logon | off |

The Designer connects the same way; it also needs the project folder once it is set (§7.2 Project).

### 10.2 Users and sign-in

- Cerebrum's own users and groups (Admin, Engineering, Operator) live in the `.ccf` block; one user per
  person, created in User and Group Management, passwords in each person's Vault area.
- No OIDC/SAML in Cerebrum: group mapping works with Windows Active Directory only (none here), web SSO
  only through EVS VIA Foundation (Keycloak). Access goes through Authentik anyway: JumpServer for the
  desktop, Traefik + Authentik forwardAuth for the web client. To record as an ADR exception.
- JumpServer: the servers are RDP assets (Windows node); the SQL instance as a **database asset**
  (Databases node, account `jumpserver_editor`, `admin_*` rights) is pending, with its main-firewall rule.

### 10.3 DHS and RCP

DHS (`by-openclaw/go-acp`) is the platform's connector: the **Northbound API** (Cerebrum XML over
WebSocket, TCP 40007, a Cerebrum user per session, one "XML" licence per session) and **RCP** (Remote
Control Protocol, HTTP 8080 / WebSocket 8081, reservations and firewall done) to control RouteMaster,
Cerebrum and devices. Pending: the DHS host's address (to narrow 40007 and 8080/8081 to it), a `svc-dhs`
Cerebrum user, `wss://` support (to check in the protocol specification).

## 11. Vault

| Path (`secret/`) | Keys | Written by |
|---|---|---|
| `dev/mssql/vm-winsql-01/BY_CEREBRUM/sa` | `user`, `password` | `cerebrum_db` (from the owner's original; old document archived) |
| `dev/mssql/vm-winsql-01/BY_CEREBRUM/cerebrum_<n>` | `user`, `password`, `ini_password_encrypted` | `cerebrum_db`; capture by `cerebrum_server` | <!-- pragma: allowlist secret (key names only) -->
| `dev/mssql/vm-winsql-01/BY_CEREBRUM/cerebrum_federated`, `jumpserver_editor` | `user`, `password` | `cerebrum_db` |
| `dev/cerebrum/<host>/app-admin` | `username`, `password`, `password_encrypted`, `service`, `instance`, `host`, `database`, `_note` | `cerebrum_server` |
| `dev/cerebrum/<host>/license` | `public_key`, `key_number` | pending |
| `dev/windows/<host>/administrator` | `password` | `windows_guest` (not applied yet) |

## 12. Open items

| Item | Owner / next |
|---|---|
| Trial key numbers (01: `111bf115`; 02: its own) | EVS |
| Multicast group for C-Link | EVS, then rows + NetBox (after lib-netbox) |
| Encrypted SQL/Admin passwords: EVS's method, or worked out from the captured pairs | EVS / owner |
| VIA Foundation's Keycloak with Authentik as identity provider | EVS |
| Northbound API over `wss://` | protocol specification (go-acp) |
| Silent `.ccf` import | EVS / manual |
| JumpServer SQL asset, split DNS, certificates, web client + RCP over TLS | pending (one PR each) |
| Syslog to Loki, SNMP hardening, email, alarm/audit settings, project folder | later |
| Windows base on these guests (CIS L1 with EVS's exceptions: UAC Never Notify, Defender exclusions; per-guest SSH host keys — all three share the template's; monitoring flag `platform_guest_stopped` still set) | pending |
| Installer store (SQL media, ODBC, sqlcmd, Bonjour, Cerebrum installer, release notes, manuals) so every playbook installs without internet; Bonjour kept meanwhile in `~/repos/_incoming/installers/bonjour/2.0.2/` | pending, next |
| Cerebrum + Watchdog started at sign-in as administrator | pending |

## 13. Troubleshooting (seen live)

| Symptom | Cause | Fix |
|---|---|---|
| SQL setup exit 0x84BE0BC2 | a restart is pending (rule `RebootRequiredCheck`), e.g. after an uninstall | the role restarts first |
| SQL setup exit 0x84B10001 "error generating the XML document" | DPAPI under a key-based SSH session (`Access is denied`) | setup as SYSTEM through task variables (the inventory's `ansible_become: false` outranks the `become` keyword) |
| Cerebrum SQL test: "Login failed", then "account is currently locked out" | a wrong password five times (Cerebrum decrypting a clear ini line, or a pre-filled field) | role unlocks with the Vault password; in the SQL tab: Ctrl+A, Delete, paste, test once |
| About: "Dependencies for the Sentinel RMS licensing need to be installed" | Sentinel persistence missing | `sentinel.yml` |
| Cerebrum SQL tester: "ODBC Driver 13 … (or later)" missing | only the legacy driver | `mssql_odbc` (Driver 17) |
| A task file missing on `main` | `.gitignore` rule `*secret*` | never name a task file `*secret*`; check `git ls-files` |
