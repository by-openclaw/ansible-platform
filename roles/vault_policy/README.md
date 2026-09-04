# role: vault_policy

Per-service Vault policy (`{svc}-{env}` scoped to `secret/{env}/{svc}/*`) + AppRole; creds `fabric/app-vault-approle-{svc}.json`.

Provisioned for 15 services by `playbooks/vault-approles.yml`.
