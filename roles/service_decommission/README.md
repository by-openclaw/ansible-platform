# role: service_decommission

Force a retired service ABSENT: dump+drop its PG db/role, archive secrets (Vault `archive/`), catalog `state: absent`. Archive-before-destroy; `-e decommission_target=<name>`.

Verified on defguard.
