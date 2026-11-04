# EVS Cerebrum — install, runbook, settings

The Cerebrum platform in the dev tier: one SQL Server instance, two Cerebrum servers (instances 01 and
02), each with its Client, Designer, Service Manager and Federation components. Everything below is
measured on the live guests (2026-11-03/04) or set by the roles named; vendor references are the
Cerebrum User Manual issue 2.9 (August 2026) and the 2.9 patch release notes (2.9.1 to 2.9.5).

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

## 2. Install, step by step

Every command runs from the repository root after this once per terminal:

```
cd ~/repos/ansible-platform && export SSH_AUTH_SOCK=~/.ssh/rune-agent.sock
```

Dry run of any step: add `--check --diff`. Each step is idempotent: run it again, it must say `changed=0`.
**Done** = applied and proven on the live hosts (2026-11-04).

| # | Step | Command | Status |
|---|---|---|---|
| 1 | Split DNS: the dev-zone names on the firewall's Unbound | `ansible-playbook playbooks/opnsense-unbound-overrides.yml` | done |
| 2 | The dev zone wildcard `*.dev.<domain>`, issued on the cert-authority host | `ansible-playbook playbooks/traefik.yml --tags cert` | done |
| 3 | SQL Server instance, logins, backup, firewall | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_db --tags sql` | done |
| 4 | SQL Server certificate (restarts the instance when it changes) | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_db --tags sql-certificate` | done |
| 5 | ODBC Driver 17 on the Cerebrum servers | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags odbc` | done |
| 6 | Windows firewall: Cerebrum's doors | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags firewall` | done |
| 7 | RCP address reservations (8080 `/v1`, `/v2`) | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags rcp` | done |
| 8 | Certificate on the Cerebrum servers (files, machine store, Security rows) | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags certificate` | done |
| 9 | EVS §3.5 on Windows: UAC Never Notify, run as administrator, Defender exclusions, hosts file | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags windows` | done |
| 10 | Start at boot: `cerebrum` (Administrators) signs in automatically; its sign-in starts Cerebrum, the Watchdog 40 s later, elevated, no time limit; a change restarts the server | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags startup` | done |
| 10a | Cerebrum at the version pin (2.9.5), with the components it has, never one more; an upgrade stops Cerebrum and restarts the server | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags install` | done |
| 11 | Sentinel persistence (licence prerequisite) | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags sentinel` | done |
| 12 | `Cerebrum.ini`: the instance's SQL connection | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags ini` | done |
| 13 | Settings rows (`_Config`) | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags settings` | done |
| 14 | Admin password in Vault; its encrypted form captured | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags admin` | done |
| 15 | NMOS registry hosts: Bonjour, 8090 reservations, firewall | `ansible-playbook playbooks/cerebrum-nmos.yml` | done |
| 16 | NMOS registry device in Cerebrum (§3.1) | Cerebrum UI, on each server | **manual, to do** |
| 17 | NMOS registry answers | `ansible-playbook playbooks/cerebrum-nmos.yml --tags validate` | after 16 |
| 18 | Licence: EVS's key per instance (Vault) into `Cerebrum.ini` (§3.3) | `ansible-playbook playbooks/cerebrum.yml --limit cerebrum_server --tags ini` | done; Cerebrum still asks for OK at start (§3.3) |
| 19 | Client and Designer, each server to the other (§3.4) | Cerebrum Client / Designer | after 18 |
| 20 | Web client and RCP over TLS (`USE_SSL`, `RCP/USE_SSL`; certificate rows already set) | Cerebrum UI, then a settings row | after 19 (plain first) |
| 21 | Certificate renewals reach every copy (Let's Encrypt renews at 60 days) | `ansible-playbook playbooks/certs-sync.yml` | done: the controller's weekly job `controller-job-certs-sync` (Monday 11:00 UTC) runs it |

Restarts: step 10 restarts a server when its start changes, step 10a after an upgrade (Cerebrum comes back
through the auto sign-in);
steps 4 and 21 restart the SQL Server instance when its certificate changes. Settings rows, the ini and the
licence are read by Cerebrum at its start.

What stays manual, and why: the NMOS registry device and the system configuration live in Cerebrum's
binary configuration block (`.ccf`, §8); the SQL and Admin passwords are typed once per new instance
because Cerebrum encrypts them with an unpublished method (§3.2); the licence key comes from EVS, and
Cerebrum asks for OK on its trial key dialog at each start (§3.3).

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
| 3.5 | UAC: Never Notify | Never notify (`ConsentPromptBehaviorAdmin` 0, `PromptOnSecureDesktop` 0; step 9) | ok | `UserAccountControlSettings` |
| 3.5 | Power: High Performance | High performance | ok | `powercfg /getactivescheme` |
| 3.5 | Visual effects: best performance | not set | gap (cosmetic) | System Properties |
| 3.5 | Firewall off, or explicit permits | on, explicit permits | ok | §9.1 |
| 3.5 | NIC power management off | not supported by the VirtIO adapter | n/a | Device Manager |
| 3.5 | Anti-virus: exclude Cerebrum processes and folders | Defender on, Cerebrum's programs, Bonjour, the install and backup folders excluded (step 9) | ok | `Get-MpPreference` |
| 3.5 | Run Cerebrum and Watchdog as administrator | set (step 9) | ok | file properties → Compatibility |
| 3.5 | Startup folder: Cerebrum, Watchdog, Witness | `cerebrum` (Administrators) signs in at boot; its sign-in starts Cerebrum, then the Watchdog 40 s later: two logon tasks, highest rights, no time limit (step 10), as EVS's own role starts it. Not a Startup-folder shortcut: with UAC on (CIS 2.3.17.6) Windows does not start a run-as-administrator program from it (measured on vm-winapp-02). No Witness (not installed). The bastion's `cerebrum` connection resumes that session | ok | Task Scheduler → `PLATFORM-cerebrum-*` |
| 3.5 | Hosts file entries on every Cerebrum server | both servers and the database host (step 9, the file written whole) | ok | `C:\Windows\System32\drivers\etc\hosts` |
| 3.5 | Explorer: extensions and hidden files shown | not set | gap (cosmetic) | Explorer options |
| 3.6 | Service Manager installed (`ServiceInstall.bat`) | `CerebrumServiceManager` Running / Automatic | ok | `services.msc` |
| NMOS | Bonjour for Windows | Bonjour 2.0.2, service Running / Automatic | ok | `services.msc`, `dns-sd` |
| NMOS | Registry URL reservations (`netsh http add urlacl`) | `http://*:8090/x-nmos/registration/` and `/x-nmos/query/` | ok (port 8090, §9.1) | `netsh http show urlacl` |
| NMOS | Registry port open in the firewall | `CEREBRUM-In-NMOS-Registry` TCP 8090 | ok | `wf.msc` |

UAC, Defender exclusions, run as administrator, start-up and hosts file are set by steps 9 and 10 (§2),
each a recorded exception to the platform's CIS baseline where it conflicts.

## 3. The manual steps in detail

### 3.1 NMOS registry device (step 16)

After step 15 (Bonjour, the 8090 reservations, the firewall rule), in Cerebrum:
Cerebrum device → 02:Services → add the Service Manager → Create New Service `nmos-registry-<n>` (and
`third-party-<n>`); on `nmos-registry-<n>` add the "Network Media Server" device (NMOS IS-04/5) with port
**8090**. Check: `http://127.0.0.1:8090/x-nmos/registration` lists the versions; every node is registered
by hand with its registry's address (no mDNS / DNS-SD).

### 3.2 First start of a new instance (once per instance)

1. Start Cerebrum. Open Configuration → **SQL**: the connection, database and user are already filled in
   by the ini. In **Password**: Ctrl+A, Delete, then paste the login's password from Vault
   `secret/dev/mssql/vm-winsql-01/BY_CEREBRUM/cerebrum_<n>`. **Test once** (expected: "Username/Password
   Correct", database does not exist yet), then Apply → OK. Five wrong passwords lock the login (§9).
2. Restart Cerebrum: it creates `Cerebrum_<n>` and asks for its Admin password: paste it from
   `secret/dev/cerebrum/<host>/app-admin`.
3. Run step 14 again: it stores both encrypted forms in Vault (`ini_password_encrypted`,
   `password_encrypted`). From then on a rebuild of that instance needs no typing.

### 3.3 Licence (step 18)

1. Sentinel must be initialised (step 11 does it; Help → About otherwise asks for `SentinelPersistanceInstall.bat`).
2. With Trial License Mode on (`GUI/DEMO_MODE_LOGON = 1`), Cerebrum shows its **public key** at start
   (instance 01: `111bf115`, instance 02: `1158cd6f`). EVS returns a key number per instance.
3. The keys go to Vault `secret/dev/cerebrum/<host>/license` (`key_number`, the vendor's field name; done
   2026-11-04 from EVS's file). Step 18 writes each into its server's `Cerebrum.ini`
   (`License:Demonstration_Key`, the line the vendor's own role writes), never shown.
4. At every start Cerebrum shows its **Cerebrum Trial Key** dialog, the key pre-filled from the ini, and
   waits for **OK** before it opens its ports (2.9.3 did the same). Confirm it on the server's console
   (the bastion's `cerebrum` connection resumes the session Cerebrum runs in). Open with EVS: whether a licensed
   server can start without the dialog (Trial License Mode off once the key is permanent?).
5. Accepted: Help → About on instance 02 (2026-11-04) reads "Cerebrum Date Limited Trial License Enabled
   (239 days of trial left to run)", i.e. until about **2027-07-01**, with the options EVS granted: redundant
   server, 4 Service Managers, 10 Client, 10 Web-Client and 10 XML licences, Router Control, Route Master
   (250 000 destinations, tie-lines, 4096 IP destinations, IP-Shuffle 128, IP-NMS off), 500 device protocol
   points, SNMP (200 devices), salvos, Tally Manager, Scheduler (5 timelines), Resource Manager (250),
   Assignment Engine (1), Package Router (1), external log server, federation.
6. The permanent licence: EVS issues it from each server's **Sentinel RMS locking code** (Help → About).
   Instance 01 (vm-winapp-01): `*1HXHUR8EJAK5SG2`; instance 02 (vm-winapp-02): `*1S5PVJQ2WKCEQA2` (both read
   2026-11-04, the same trial and options on both; Cerebrum writes the code to no file).

### 3.4 Client and Designer test (step 19)

On each server, the Client logs on to the **other** server (srv1 → srv2 and back), then the Designer.
Values in §10.1. Proves the firewall, C-Link and the logins.

### 3.5 Rebuild of an existing instance

The playbook replays everything, including the two encrypted passwords captured in 3.2 (the ini line
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
| Version | 2.9.5 (EVS, 03-11-2026: the web client fix of 2.9.4's CS142320), upgraded from 2.9.3 by step 10a | installer from the installer store (`platform_installer_store`), sha256 pinned |
| Components installed | `cerebrum`, `cerebrum\cerebrum_watchdog`, `cerebrum_designer`, `cerebrum_client`, `cerebrum_service_manager`, `cerebrum_federation`, `gilze_clfs` (EVS Media Infrastructure Device UI's) | read from the installer's record (`Inno Setup: Selected Components`); not installed: `cerebrum_witness`, `cerebrum_database_mirror_creator`, `cerebrum_sdn` |
| Unattended switches | `/InstallSentinel=… /InstallSQL=Skip /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /DIR=… /COMPONENTS=… /LOG=…` | EVS's own playbook; manual §3.4 `/HELP`. An upgrade: the installed components, `Skip` for Sentinel, the same folder (release notes, Warnings) |
| Sentinel driver | Sentinel System Driver Installer 7.6.1 | not on the SQL server |
| Sentinel RMS persistence | `Sentinel_Init.exe`, then marker `HKLM\SOFTWARE\WOW6432Node\EVS Broadcast Equipment\Cerebrum\Sentinel` `installed=1` | the vendor's `SentinelPersistanceInstall.bat` pauses and does not wait; the role waits and marks |
| ODBC | Driver 17 for SQL Server 17.11.1.1 | Cerebrum's SQL tester looks up 17, 13, 11, Native Client by name, not 18 |
| Start | at boot: auto sign-in of `cerebrum`, then Cerebrum, the Watchdog 40 s later, elevated, no time limit (step 10) | then the trial key dialog (§3.3); the bastion's `cerebrum` connection resumes that session |

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

### 9.3 Names and certificates (steps 1, 2, 4, 8)

Split DNS (naming/0001 §7: the env sub-domain), on the firewall's Unbound — the resolver the guests use
(10.1.3.1) — never published; catalog `inventories/prod/group_vars/opnsense.yml`, tier and address from
the inventory:

| Name | Answer | Kind |
|---|---|---|
| `vm-winapp-01.dev.<domain>`, `vm-winapp-02.dev.<domain>`, `vm-winsql-01.dev.<domain>` | .201, .202, .203 | asset (A + PTR) |
| `cerebrum-01.dev.<domain>`, `cerebrum-02.dev.<domain>` | .201, .202 | instance (service) |
| `cerebrum-db.dev.<domain>` | .203 | SQL instance `BY_CEREBRUM` (service) |
| `nmos-registry-01.dev.<domain>`, `nmos-registry-02.dev.<domain>` | .201, .202 | NMOS registry (service) |

No AAAA: the guests have no static ULA address yet.

Certificate: **one zone wildcard `*.dev.<domain>`** (naming/0001 §8), not the prod one (a dev host would
hold the prod key). Let's Encrypt, RSA 2048 (EVS manual §5.2.3), issued once on the cert-authority host
(`roles/traefik` `traefik_zone_wildcards: [dev]`, its own timer `lego-renew-zone-dev`); the Cloudflare
token never leaves that host. Copies, by `roles/tls_cert` `windows.yml`:

| Where | What | Check |
|---|---|---|
| `C:\ProgramData\<org>\tls\` on the three guests | `wildcard.crt`, `wildcard.key`, `wildcard.pfx` — folder SYSTEM + Administrators only | `icacls C:\ProgramData\<org>\tls` |
| Machine store `LocalMachine\My` | `CN=*.dev.<domain>`, key in machine storage, non-exportable; older ones of the name removed | `certlm.msc` → Personal |
| Cerebrum rows (both instances) | `SECURITY/CERTIFICATE`, `KEY` (the files above), `CERT_HASH` (the thumbprint) | Configuration → Security; TLS itself stays off until step 20 |
| SQL Server `BY_CEREBRUM` | `SuperSocketNetLib\Certificate` = thumbprint; key readable by `NT SERVICE\MSSQL$BY_CEREBRUM`; encryption not forced | ERRORLOG: "The certificate … was successfully loaded for encryption" |

A renewal (every 60 days) reaches the copies with step 21, the controller's weekly job; Cerebrum reads the
new thumbprint at its next start, SQL Server is restarted by the step.

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
- JumpServer: the three servers are RDP assets (Windows node). A **database asset for SQL Server is not
  possible on JumpServer CE** (measured 2026-11-04: its database platforms are MariaDB, MongoDB, MySQL,
  PostgreSQL, Redis; SQL Server is an Enterprise feature). The login `jumpserver_editor` exists
  (db_datareader + db_datawriter). Open choice: an RDP session to a host with SSMS, JumpServer EE, or a
  web SQL client behind Traefik + Authentik. The bastion reaches the guests with its own address
  (10.1.3.221, no address translation): admitting it to SQL is one entry in `cerebrum_db_allowed_from`.

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
| `dev/cerebrum/<host>/license` | `key_number` | imported once from EVS's file (2026-11-04); read by `cerebrum_server` (step 18) |
| `dev/cerebrum/<host>/run-user` | `user`, `password` | `cerebrum_server` (the account that signs in at boot); read by the bastion (`cerebrum` connection) |
| `dev/windows/<host>/administrator` | `password` | `windows_guest`; read by the bastion (`Administrator` connection) |

## 12. Open items

| Item | Owner / next |
|---|---|
| Cerebrum stops at its trial key dialog at every start (key pre-filled; OK through the bastion's `cerebrum` connection): an unattended start for a licensed server | EVS |
| Permanent licences before the trial ends (about 2027-07-01): the two locking codes to EVS (§3.3) | owner → EVS |
| Multicast group for C-Link | EVS, then rows + NetBox (after lib-netbox) |
| Encrypted SQL/Admin passwords: EVS's method, or worked out from the captured pairs | EVS / owner |
| VIA Foundation's Keycloak with Authentik as identity provider | EVS |
| Northbound API over `wss://` | protocol specification (go-acp) |
| Silent `.ccf` import | EVS / manual |
| SQL access through the bastion: JumpServer CE has no SQL Server (§10.2) | owner's choice |
| Web client + RCP over TLS (step 20) | after the licence |
| Syslog to Loki, SNMP hardening, email, alarm/audit settings, project folder | later |
| Windows base on these guests (CIS L1 with EVS's exceptions: UAC Never Notify, Defender exclusions; per-guest SSH host keys — all three share the template's; monitoring flag `platform_guest_stopped` still set) | pending |
| Installer store: **one place, the controller** (`platform_installer_store` = `~/repos/_incoming/installers/`, outside git, one folder per product and version with `SHA256SUMS` + `SOURCE.txt`): SQL 2025 Express, sqlcmd 17.0.4055.5, ODBC 17.11.1.1, Cerebrum 2.9.3 and 2.9.5 (+ release notes, manuals), Bonjour 2.0.2, WebView2 Evergreen x64 (2026-11-04). Cerebrum installs from it (step 10a), WebView2 too where it is missing (it then updates itself); the object store's route refuses the dev guests (403): the move comes with the new infrastructure, one value to change (owner 2026-11-04) | with the new infrastructure |

## 13. Troubleshooting (seen live)

| Symptom | Cause | Fix |
|---|---|---|
| SQL setup exit 0x84BE0BC2 | a restart is pending (rule `RebootRequiredCheck`), e.g. after an uninstall | the role restarts first |
| SQL setup exit 0x84B10001 "error generating the XML document" | DPAPI under a key-based SSH session (`Access is denied`) | setup as SYSTEM through task variables (the inventory's `ansible_become: false` outranks the `become` keyword) |
| Cerebrum SQL test: "Login failed", then "account is currently locked out" | a wrong password five times (Cerebrum decrypting a clear ini line, or a pre-filled field) | role unlocks with the Vault password; in the SQL tab: Ctrl+A, Delete, paste, test once |
| About: "Dependencies for the Sentinel RMS licensing need to be installed" | Sentinel persistence missing | `sentinel.yml` |
| Cerebrum SQL tester: "ODBC Driver 13 … (or later)" missing | only the legacy driver | `mssql_odbc` (Driver 17) |
| A task file missing on `main` | `.gitignore` rule `*secret*` | never name a task file `*secret*`; check `git ls-files` |
| After a restart the Watchdog runs, Cerebrum does not | one logon task with two actions: Task Scheduler waits for the first (the Watchdog) to end | two logon tasks (step 10, #1110) |
| Port 40001 closed although `Cerebrum.exe` runs (34 MB, idle) | the **Cerebrum Trial Key** dialog waits for OK in `cerebrum`'s session | OK through the bastion's `cerebrum` connection (§3.3) |
| "Only one instance of this application may be run on a PC at a time" | Cerebrum already runs in `cerebrum`'s session; it was started again from another session (`<org>`, `Administrator`) | connect as `cerebrum` on the bastion: the connection resumes the running session |
| Cerebrum and its Watchdog stop three days after a start | Windows' default task time limit (72 h) | `execution_time_limit: PT0S` (step 10) |
| The bastion's `Administrator` login refused | the guest's password differs from Vault: cloudbase-init's password plugin reset it at a boot (2026-10-25, 2026-10-30) | `roles/windows_guest` sets Vault's password again |
| Hosts file down to a few lines, `win_hosts`: "Stream was not readable" | the module rewrote the file per entry; a failed write after the truncation | the file written whole (step 9, #1110) |
