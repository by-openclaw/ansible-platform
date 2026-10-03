# Nextcloud — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: nextcloud`). Role `roles/nextcloud`, play `playbooks/nextcloud.yml`, guest `lxc-nextcloud-01`. Audit: [`docs/audits/nextcloud-2026-10-02.md`](../audits/nextcloud-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication`, `identity/0002-provisioning`, `naming/0002-identity`.
2. **Authentik application:** slug `nextcloud` (`group_vars/all/sso.yml`), provider OAuth2/OIDC, scopes `openid profile email groups`, redirect `https://nextcloud.<domain>/apps/user_oidc/code`, logout URI registered; the Nextcloud side is the `user_oidc` app, provider id `authentik` (`nextcloud_oidc_provider_id`).
3. **Access model:** IdP-enforced — only `nextcloud-users` may log in (`restrict_to_group: true`); members of `nextcloud-admins` are mapped into the Nextcloud `admin` group (`admin_source_group`). Groups are provisioned from the IdP claim (today every platform group — audit gap 9).
4. **Vault paths:** `secret/{env}/nextcloud/admin` (break-glass local admin, bootstrap-created, rotated by Ansible), `secret/{env}/nextcloud/db-pgsql` (minted by `postgres_db`), `secret/{env}/nextcloud/oidc` (minted by `roles/authentik`); shared: Redis password (`roles/redis`), S3 primary-storage credentials.
5. **Ansible adapter + vars:** `roles/nextcloud/tasks/post-install.yml` (occ: SSO, trusted proxies, policies), `tasks/groups.yml` (retired platform groups absent, orphan report), `tasks/team-bindings.yml` (group folder, Talk room, calendar + address book per group); single sources `group_vars/all/{people,identity,sso}.yml`.
6. **Removal notes:** a person leaves via `people.yml` (`state: disabled`, never deleted — identity/0001); the IdP stops the login, the account and its files stay for the retention period; service removal = `playbooks/decommission-service.yml`.

## Notifications (services/0005)

1. **Transport:** SMTP to `vm-mailcow-01.<domain>:587` STARTTLS (`mail_smtpmode smtp`, `mail_smtpsecure tls`), sender `nextcloud@<domain>`; credentials from the mailbox role, not in this role.
2. **What is sent:** share/activity/Talk notifications to users; admin notifications to the `admin` group; the Mail app is provisioned for every SSO user (`nextcloud_mail_provisioning`).
3. **Alerting path:** service-down → Prometheus blackbox (`/status.php`, `/`, signaling, recording) → Alertmanager → Discord/mail (platform); application metrics: Prometheus job `nextcloud` (serverinfo API via `nextcloud-exporter`, `:9205` to the monitoring host only).
4. **Logs:** container stdout → journald → promtail → Loki (`container="nextcloud"`); application log `nextcloud.log` → promtail job `nextcloud_app` with `audit="true"` and the CrowdSec agent (`crowdsecurity/nextcloud`, bans at Traefik).
5. **Operator contact:** `docs/register.md` row (owner Youssef Boujraf).

## Backup (infra/0008)

Class A + C (`docs/backup.md`): PostgreSQL in the shared cluster (daily `pg_dumpall` + PBS of the DB guest), the `nextcloud-app` volume (config, apps) in PBS (ct 503, daily), **files on S3 primary storage** (external bucket) mirrored daily into the platform S3 (`seaweedfs_mirrors`, 30-day trash) until the primary moves on-prem.
