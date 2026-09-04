# role: vault_deploy_identity

The `ansible-deploy` AppRole + policy (secret CRUD under `{env}`/archive, `sys/policies/acl/*`, `auth/approle/role/*`, raft snapshot, `sys/audit` **without delete**). **Self-maintains** via its own AppRole; root only at genesis.

Play: `playbooks/vault-deploy-identity.yml`.
