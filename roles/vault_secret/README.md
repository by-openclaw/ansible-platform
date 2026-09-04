# role: vault_secret

Get-or-create a KV v2 secret (`vault_secret_path` + `vault_secret_init`), read-only when `init` is empty, **rotation mode** via `vault_secret_force_fields`. Publishes `vault_secret_result`.

Auth through `vault_login` (AppRole).
