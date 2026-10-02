# Authentik — the identity provider (lxc-authentik-01)

Setup and operations live in [`roles/authentik/README.md`](../../roles/authentik/README.md); this
page holds the two per-tool documents the ADRs require (identity/0002 §identity.md,
services/0005 §notifications.md) and points at everything else. Audit: [`audits/authentik-2026-10-02.md`](../audits/authentik-2026-10-02.md).

## identity.md (identity/0002)

1. **ADR:** `doc-platform-core/docs/adr/identity/0002-provisioning.md` (and identity/0001, identity/0004).
2. **Authentik applications:** Authentik is the IdP itself; every application it publishes is one
   entry in [`inventories/prod/group_vars/all/sso.yml`](../../inventories/prod/group_vars/all/sso.yml)
   (`authentik_oidc_apps` — slug, launch URL, access group, Vault path, redirect URIs;
   `authentik_proxy_apps` — forwardAuth apps). The LDAP outpost serves the directory to tools without
   OIDC (`roles/authentik/tasks/ldap.yml`).
3. **Vault paths:** `secret/prod/authentik/admin` (secret key + bootstrap admin `akadmin`),
   `secret/prod/authentik/db-pgsql` (own PostgreSQL user), `secret/prod/authentik/ldap-outpost`,
   `secret/prod/authentik/user-<username>` (one per person), `secret/prod/<service>/oidc` (one per
   OIDC client, minted by this role), `secret/prod/mail/authentik` (mailbox).
4. **Ansible adapter + vars:** `roles/authentik` (blueprints rendered from
   `templates/identity.yaml.j2`, `oidc-app.yaml.j2`, `proxy-apps.yaml.j2`); vars =
   `inventories/prod/group_vars/all/{people,identity,sso}.yml`. Play: `playbooks/authentik.yml`;
   `--check` first, always.
5. **Group → role mapping:** `platform_service_groups` in
   [`identity.yml`](../../inventories/prod/group_vars/all/identity.yml) (`{service}-users` /
   `{service}-admins`; `platform-admins` = Authentik superusers) — people hold groups in
   [`people.yml`](../../inventories/prod/group_vars/all/people.yml). No copy here.
6. **Removal notes:** a person is `state: disabled` in people.yml (never deleted — identity/0001);
   an application leaves `sso.yml` and, for forwardAuth apps, is named in
   `authentik_proxy_apps_retired` (blueprints only add); `playbooks/decommission-service.yml` removes
   a service's app, group and Vault client.

## notifications.md (services/0005)

1. **ADR:** `doc-platform-core/docs/adr/services/0005-notifications.md`.
2. **Events the tool fires:** none to a channel. Authentik sends e-mail only: password recovery,
   MFA/enrolment links, administrative notifications to the admin group.
3. **Channels:** e-mail to the person (recovery/enrolment); administrative mail to `platform-admins`.
   No Discord/Teams channel. Platform alerts about Authentik (probe down, TLS expiry) come from
   Prometheus/Alertmanager, not from Authentik.
4. **Template:** Authentik's own mail templates (vendor); no platform template override.
5. **SMTP:** the service mailbox `authentik@<domain>` on Mailcow, submission :587 STARTTLS, from =
   the service address (`roles/authentik/tasks/secrets.yml` → `AUTHENTIK_EMAIL__*`, credentials
   from `secret/prod/mail/authentik`).

## Related

- Backup class **A + D** — [`docs/backup.md`](../backup.md); licensing — [`docs/licensing.md`](../licensing.md).
- Runbook: `roles/authentik/README.md`.
