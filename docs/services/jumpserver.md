# JumpServer — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: jumpserver`). Role `roles/jumpserver` (+ `files/reconcile.py`), play `playbooks/jumpserver.yml`, guest `lxc-jumpserver-01` (ct 571). Audit: [`docs/audits/jumpserver-2026-10-02.md`](../audits/jumpserver-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — OpenID Connect against Authentik (`jumpserver_oidc_enabled`), users auto-provisioned; the bastion's asset access uses the platform break-glass identity vaulted in JumpServer (key + passphrase from Vault at reconcile time, shredded afterwards).
2. **Authentik application:** OIDC, slug `jumpserver` (`group_vars/all/sso.yml`).
3. **Access model:** people sign in through Authentik; the `bastion-admins` group and its permission to every asset are reconciled from the catalog (`reconcile.py`); assets = every managed host on the hardening baseline (`:22222`, the local break-glass admin, sudo with the escrowed password). Local `admin` of JumpServer = break-glass (password in Vault).
4. **Vault paths:** `secret/{env}/jumpserver/app` (SECRET_KEY, BOOTSTRAP_TOKEN, DB and Redis passwords), `jumpserver/oidc` (`roles/authentik`), `jumpserver/s3` (`seaweedfs_bucket`, session replays), `mail/jumpserver` (service mailbox), `break-glass/ssh-key` + `break-glass/ssh-passphrase` (read only inside the reconcile).
5. **Ansible adapter + vars:** `roles/jumpserver` (`defaults/main.yml`: pin, ports, OIDC endpoints, bastion group, asset baseline; `tasks/main.yml` the five containers + bundled PostgreSQL/Redis through `service_scaffold`; `tasks/reconcile.yml` + `files/reconcile.py` = settings, users, groups, assets, permissions, replay storage, email — idempotent).
6. **Removal notes:** `playbooks/decommission-service.yml`; class B — the bundled database volume (audit trail, sessions) and the replay bucket `jumpserver-replays` are archived before destroy.

## Notifications (services/0005)

1. **Transport:** SMTP through the `jumpserver@<domain>` mailbox (one document: `mail/jumpserver`), STARTTLS 587 — login/approval mails to users.
2. **What is sent:** JumpServer user notifications; nothing to operators by mail.
3. **Alerting path:** Prometheus blackbox `https://jumpserver.<domain>/` → Alertmanager → Discord/mail (platform); JumpServer CE exposes Prometheus metrics only with an API token (not scraped).
4. **Logs:** the seven containers → journald → promtail → Loki; session replays in S3 (`jumpserver-replays`); the command/session audit lives in JumpServer's database.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B (`docs/backup.md`): the bundled PostgreSQL volume (users, assets, audit) and the configuration in PBS (daily, ct 571); session replays in the replicated S3 bucket. Restore = play + PBS volume.
