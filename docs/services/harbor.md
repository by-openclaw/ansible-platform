# Harbor — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: harbor`). Role `roles/harbor`, play `playbooks/harbor.yml` (+ `harbor-upgrade.yml` ladder), guest `lxc-harbor-01` (ct 590). Audit: [`docs/audits/harbor-2026-10-02.md`](../audits/harbor-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — Harbor `auth_mode: oidc_auth` against Authentik (scopes `openid,email,profile,groups`, `preferred_username`, auto-onboard), switched by the role after install.
2. **Authentik application:** OIDC, slug `harbor` (`group_vars/all/sso.yml`), bound to `harbor-users`.
3. **Access model:** only `harbor-users` may sign in (IdP binding); members of `harbor-admins` are Harbor administrators (`oidc_admin_group`); self-registration off; project creation admin-only (projects come from the role: `gitlab` private, `dockerhub` proxy cache, `library` private). CI pushes with the scoped system robot `robot$gitlab-ci` (secret in Vault). Break-glass: the local `admin` account, its password in Vault (`harbor/admin`).
4. **Vault paths:** `secret/{env}/harbor/admin`, `harbor/db-pgsql` (`postgres_db`), `harbor/s3` (`seaweedfs_bucket`), `harbor/oidc` (`roles/authentik`), `harbor/robot-gitlab`.
5. **Ansible adapter + vars:** `roles/harbor` (`defaults/main.yml`: version ladder target, S3, DB, OIDC, metrics, settings and schedules; `templates/harbor.yml.j2` = the installer configuration; `tasks/settings.yml` = every system setting and schedule through the API).
6. **Removal notes:** `playbooks/decommission-service.yml`; class B + C — the PostgreSQL database and the S3 bucket `harbor-registry` are archived before destroy; robots and the OIDC client are catalog entries declared `absent`.

## Notifications (services/0005)

1. **Transport:** none — Harbor sends no mail here; webhooks are per project (none configured).
2. **What is sent:** nothing to operators from the product.
3. **Alerting path:** Prometheus — blackbox `https://harbor.<domain>/` plus the `harbor` job (`:9090/metrics`: core, registry, jobservice and exporter series) → Alertmanager → Discord/mail (platform rules).
4. **Logs:** the components log through the syslog driver into the `harbor-log` sidecar → `/var/log/harbor/<component>.log` → promtail (`harbor_components`); the forwarded audit log → `/var/log/harbor/audit.log` → promtail with the `audit` label (`harbor_audit`); the database keeps 180 days of audit rows (weekly purge).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B + C (`docs/backup.md`): metadata in the shared PostgreSQL cluster (daily `pg_dumpall`), blobs in the S3 bucket `harbor-registry` (SeaweedFS, replicated off-site), guest image in PBS (daily, ct 590; `/data` holds only logs and the Trivy cache). Restore = play + database restore; blobs are already there.
