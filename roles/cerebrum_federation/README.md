# role: cerebrum_federation

EVS Cerebrum's Federation service (user manual issue 2.9, §13 p.270–271): it shares sources and destinations
between Cerebrum systems from its own SQL database. Two machines run it (primary, secondary); the inventory
group `cerebrum_federation` names them, primary first. An empty group applies nothing.

## What it does, in order

1. Refuses a host where the service's C-Link port (TCP 40003 by default) is Cerebrum's own: a Cerebrum
   server uses 40001–40005 itself. The manual's separate machines, or another port agreed with EVS.
2. `CerebrumFederationService.ini`, "the same format as the Cerebrum server": one line per declared key
   (`SQL:USE_DEFAULT`, `SQL:LOGIN_CREDENTIALS`, `SQL:LOGIN_USERNAME`, `SQL:PRIMARY_CONNECTION` by FQDN,
   `SQL:DATABASE=Federation`), every other line kept. The password line is never written in clear (an
   encrypted line decrypted to a wrong password locks the SQL login after five tries): entered once in the
   form EVS confirms, captured into Vault (`ini_password_encrypted_federation` on the login's document),
   replayed afterwards.
3. The Windows service as EVS's `FederationServiceInstall.bat` creates it — automatic start, restart on
   failure (1, 2, 5, 10 s; reset after 1 h), LocalSystem — started only once the ini holds a password.
4. One inbound rule `CEREBRUM-In-Federation-TCP`: the Cerebrum servers to the service's port, bound to
   `CerebrumFederationService.exe`.

Not in this role: the database login (`roles/cerebrum_db`, `cerebrum_federated`), the database's backup and
grants (`roles/cerebrum_db` once `Federation` exists), and Cerebrum's own "Federation Service" tab (enable,
the two FQDNs, a restart of both Cerebrum servers — `roles/cerebrum_server` settings rows, mapped at the
install).

Run: `ansible-playbook playbooks/cerebrum.yml --tags federation`.

## Controls

| Control | Where |
|---|---|
| ISO 27001 A.8.5, A.5.17 | the database login from Vault; no clear password on disk |
| ISO 27001 A.8.20 | one inbound rule, bound to the program, open to the Cerebrum servers only |
| ISO 27001 A.8.9 | every setting a variable; the ini's other lines untouched |
