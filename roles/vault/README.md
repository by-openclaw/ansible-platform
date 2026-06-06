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
