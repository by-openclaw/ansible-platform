# Vaultwarden — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: vaultwarden`). Role `roles/vaultwarden`, play `playbooks/vaultwarden.yml`, guest `lxc-vaultwarden-01`. Audit: [`docs/audits/vaultwarden-2026-10-02.md`](../audits/vaultwarden-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — native OIDC (`SSO_ENABLED`, `SSO_ONLY`: every login goes through Authentik; the master password stays the vault's encryption key, not a login).
2. **Authentik application:** OIDC, slug `vaultwarden` (`group_vars/all/sso.yml`), scopes `email profile offline_access`, redirect `/identity/connect/oidc-signin`, `force_email_verified`.
3. **Access model:** IdP-enforced — only `vaultwarden-admins` may log in today (`restrict_to_group`); self-signup off (`SIGNUPS_ALLOWED=false`), accounts are created by the first SSO login (`SSO_SIGNUPS_MATCH_EMAIL`). Break-glass: the `/admin` panel with `ADMIN_TOKEN`, reachable from internal + admin sources only.
4. **Vault paths:** `secret/{env}/vaultwarden/admin` (admin token), `secret/{env}/vaultwarden/oidc` (minted by `roles/authentik`), `secret/{env}/vaultwarden/db-pgsql` (minted by `postgres_db`), `secret/{env}/mail/vaultwarden` (service mailbox).
5. **Ansible adapter + vars:** `roles/vaultwarden` (`vars/main.yml` = the whole environment; `service_scaffold` for DB, mailbox, containers, route with the `/admin` endpoint).
6. **Removal notes:** `playbooks/decommission-service.yml`; class A — the PostgreSQL database and the `vaultwarden-data` volume (attachments, sends, RSA key) are archived before destroy.

## Notifications (services/0005)

1. **Transport:** SMTP to `vm-mailcow-01.<domain>:587` STARTTLS as the service mailbox `vaultwarden@<domain>` (credential from Vault, minted by `roles/mailbox`).
2. **What is sent:** invitations, new-device and 2FA mails, emergency-access and organisation mails to users; nothing to operators.
3. **Alerting path:** Prometheus blackbox `https://vaultwarden.<domain>/` → Alertmanager → Discord/mail (platform); no application metrics (the product exposes none; `/alive` is probed).
4. **Logs:** container stdout → journald → promtail → Loki (`container="vaultwarden"`); organisation event log inside the product (`ORG_EVENTS_ENABLED`, 90 days).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class A (`docs/backup.md`): database in the shared PostgreSQL cluster (daily `pg_dumpall`), `vaultwarden-data` volume in PBS (daily, ct 502).
