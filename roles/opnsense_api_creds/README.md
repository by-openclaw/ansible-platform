# role: opnsense_api_creds

Concern-role: reads the OPNsense MVC API key/secret from HashiCorp Vault (`<env>/opnsense/api`, fields `key`/`secret`) via the ansible-deploy AppRole and publishes them as facts — `opn_key`/`opn_secret` (catalog names) and `opnsense_api_key`/`opnsense_api_secret` (role names). Include it as the first `pre_task` of every play that talks to the firewall API. Replaces the ansible-vault-encrypted `group_vars/all/vault.yml` (security/0001: Vault is the secret store; no second secret mechanism in git).

Delegation note: the FW host is `ansible_connection: local` (API-only); the Vault read is delegated to `lxc-vault-01`, which is SSH because the inventory sets `ansible_connection: ssh` for every host except the FW.
