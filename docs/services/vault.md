# Vault — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: vault`). Role `roles/vault` (+ `roles/vault_deploy_identity`, `roles/vault_login`, `roles/vault_secret` as the consumers' concern roles), play `playbooks/vault.yml`, guest `lxc-vault-01`. Audit: [`docs/audits/vault-2026-10-03.md`](../audits/vault-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — OIDC auth method against Authentik (role `default`, the Authentik group `vault-admins` → Vault external group → policy `admins`); machines authenticate with AppRole (`ansible-deploy` for the controller, one `<service>-prod` policy per service).
2. **Authentik application:** OIDC confidential client, slug `vault` (`group_vars/all/sso.yml`), redirects: the UI callback and `http://localhost:8250/oidc/callback` (the `vault login -method=oidc` CLI); access restricted to `vault-admins`.
3. **Access model:** humans = `vault-admins` → `admins` (full, with `sudo`); the controller = AppRole `ansible-deploy` (CRUD under `secret/{env}/*` + archive, no seal/rekey/root/audit control); services = AppRoles with their `<service>-prod` policy (own paths only); the raft snapshot = token with the `snapshot` policy (root-only file on the host). The root token is revoked in steady state (SEC-06); genesis operations (`vault_genesis=true`) run after `vault operator generate-root`.
4. **Vault paths (Vault's own):** `secret/{env}/vault/oidc` (the client, minted by `roles/authentik`); the unseal keys + genesis material live in the controller's bootstrap file (the sanctioned exception) — off-platform custody is the open SEC-06 item.
5. **Ansible adapter + vars:** `roles/vault` (`defaults/main.yml`: image pin, listener, raft, TLS = the platform wildcard, KV path, OIDC; `tasks/container.yml` (scaffold container, audit dir + promtail ACL), `init.yml` (init/unseal), `audit.yml` (file device), `kv.yml` + `oidc.yml` (genesis only), Traefik route internal-only); `roles/vault_deploy_identity` (the deploy AppRole + policy).
6. **Removal notes:** not removable — every service reads its secrets here. Rebuild = play + `operator raft snapshot restore` (snapshots daily on the host, in the PBS guest image) + unseal with the key shares.

## Notifications (services/0005)

1. **Transport:** none — Vault sends no mail; the host's postfix relay carries system mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus blackbox `https://vault.<domain>/` (sealed = probe fails) + `node` + `cadvisor` → Alertmanager → Discord/mail. Vault's own telemetry (`/v1/sys/metrics`) is not scraped: the listener change re-seals Vault — the owner's window.
4. **Logs:** the audit device `file` → `/var/log/vault/audit.log` (0640, promtail `vault_audit` with the `audit` label), the container on journald.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class A (`docs/backup.md`): `vault-snapshot.timer` 02:15 → `operator raft snapshot save` → `/var/lib/vault/snapshots/` (0600, 14 days by tmpfiles) → PBS daily guest image (encrypted, replicated off-site with the datastore); restore = `operator raft snapshot restore -force` + unseal (3 of 5 key shares). The data at rest is sealed with the Shamir keys; the raft snapshot carries sealed data.
