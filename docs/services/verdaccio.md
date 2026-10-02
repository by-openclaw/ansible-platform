# Verdaccio — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: verdaccio`). Role `roles/verdaccio`, play `playbooks/verdaccio.yml`, guest `lxc-verdaccio-01` (ct 505). Audit: [`docs/audits/verdaccio-2026-10-02.md`](../audits/verdaccio-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — the `verdaccio-openid` plugin: web and `npm login` go through Authentik (OIDC, `preferred_username`, `groups` claim); `keep-passwd-login` stays on for the one CI service account.
2. **Authentik application:** OIDC, slug `verdaccio` (`group_vars/all/sso.yml`), bound to `verdaccio-users`.
3. **Access model:** only `verdaccio-users` may authenticate (IdP binding + the plugin's `authorized-groups`); every package route is `$authenticated` (no anonymous reads); `@<company>/*` is the private scope, everything else proxies npmjs. The CI publisher `svc-verdaccio-<env>` is a local htpasswd account whose credential lives in Vault — the only non-SSO principal, by design.
4. **Vault paths:** `secret/{env}/verdaccio/registry` (the service account), `verdaccio/oidc` (`roles/authentik`), `verdaccio/s3` (`seaweedfs_bucket`).
5. **Ansible adapter + vars:** `roles/verdaccio` (`defaults/main.yml`: base image + plugin pins, uplink, scope; `templates/config.yaml.j2` = the whole configuration; `templates/Dockerfile.j2` builds the platform image with the S3 and OpenID plugins; `service_scaffold` for the bucket, route and container).
6. **Removal notes:** `playbooks/decommission-service.yml`; class C — the S3 bucket `verdaccio` (packages + package db) is archived before destroy; the OpenID token store under `/opt/verdaccio/storage` goes with the guest.

## Notifications (services/0005)

1. **Transport:** none — Verdaccio sends no mail (`mailbox: false`; the mailbox created before this audit stays at Mailcow, never deleted).
2. **What is sent:** nothing.
3. **Alerting path:** Prometheus — blackbox `https://npm.<domain>/` → Alertmanager → Discord/mail (platform); Verdaccio 6 exposes no Prometheus metrics and no plugin for it exists on npm (`/-/ping` is the health signal).
4. **Logs:** container stdout (level `http`, every request) → journald → promtail → Loki (`container="verdaccio"`); the `audit` middleware is on.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class C (`docs/backup.md`): packages and the package database in the S3 bucket `verdaccio` (SeaweedFS, replicated off-site); the guest image in PBS (daily, ct 505) holds the configuration and the OpenID token store. Restore = play (the bucket is already there).
