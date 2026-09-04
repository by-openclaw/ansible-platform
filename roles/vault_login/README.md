# role: vault_login

Shared Vault auth: logs in with the `ansible-deploy` AppRole (verified TLS, FQDN — skip-verify banned) and sets `vault_deploy_token`.

Creds: `secrets/app-vault-approle-ansible-deploy.json` (bootstrap, not fabric).
