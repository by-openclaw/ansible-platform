# role: vault (Docker)

HashiCorp **Vault** (secrets backend) on `lxc-vault-01` (SVC `10.1.3.150`).
Integrated **raft** storage, TLS via the shared wildcard cert, fronted by Traefik
(internal-only). Upgrade = bump `vault_image` tag (raft data persists in the
`vault-data` volume). Single node now; raft is HA-adoptable.

- Pinned `hashicorp/vault` image; depends `base` + `docker` (nested LXC).
- `disable_mlock = true` (avoids the IPC_LOCK cap in an unprivileged LXC).
- TLS: wildcard cert via `tls_cert` mounted RO (owned by the container vault uid
  100); listener on `:8200` HTTPS. CA store mounted.
- **Init/unseal (idempotent):** first run `operator init` (5 shares / 3 threshold)
  → unseal keys + root token stored ONCE in the controller secret store
  (`vault-init.json`, `0600`, `no_log`, **CRITICAL — back this up**). On a restart
  Vault seals; the role re-unseals from the stored keys. Auto-unseal (transit/KMS)
  = follow-up.
- Published on `10.1.3.150:8200` + `127.0.0.1:8200`. Cert renewal = SIGHUP reload
  (no seal); config change = restart (re-unseals).
- **Internal-only** via `traefik_route` (`vault.by-research.be`); the Traefik
  backend is the node FQDN over HTTPS so the wildcard cert verifies.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/vault.yml`.
Needs the FW DMZ→SVC `:8200` rule + Unbound overrides (opnsense catalog).

## People reading in Vault (security/0001)

A login that automation creates and uses stays in Vault only; the people entitled to it read
it there, read-only, after signing in through the identity provider.

- **Declared in the inventory:** `platform_service_logins` (the login document of a service) and
  `platform_service_groups` (its `admin` group). A document that also holds machine-only values
  is not declared: split it first. The `root` accounts and the break-glass documents are the
  emergency kit's, not a group's.
- **Per group:** the policy `people-<group>` (read on the documents, the names of their
  folders), an external group of the same name carrying it, mapped to the provider's group.
- **Run:** `ansible-playbook playbooks/vault.yml --tags people --limit <first member>` — applies
  on a difference and proves every group: a login that carries one group's policy and nothing
  else is asked for its capabilities (`read` on its documents, `deny` on another). No document is
  read for the proof, and the login is removed.
