# SeaweedFS — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: seaweedfs`, alias `seaweedfs` for the admin console). Role `roles/seaweedfs` (+ `roles/seaweedfs_bucket` consumed by every S3 tenant), play `playbooks/seaweedfs.yml`, guest `lxc-seaweedfs-01` (ct 550, `/data` = the ZFS dataset `tank/data/seaweedfs` bind-mounted from the node). Audit: [`docs/audits/seaweedfs-2026-10-02.md`](../audits/seaweedfs-2026-10-02.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — the admin console sits behind Traefik forwardAuth (Authentik, the SeaweedFS admin group); the S3 API authenticates machines with scoped identities (one per tenant, minted by `roles/seaweedfs_bucket`, stored in the filer's IAM config); the master/volume/filer APIs are reachable from the platform ranges only.
2. **Authentik application:** forwardAuth on `seaweedfs.<domain>` (`group_vars/all/sso.yml`); no OIDC client of its own.
3. **Access model:** people → the console through Authentik (admin group), then the console's own login (vendor requirement for a non-loopback bind; credential in Vault); machines → S3 with their tenant identity (bucket-scoped actions); the `admin` S3 identity is the role's own (bucket provisioning) — break-glass for S3.
4. **Vault paths:** `secret/{env}/seaweedfs/admin` (the S3 admin identity + the SSE key-encryption key), `seaweedfs/console` (console login), `offsite/s3` (the Contabo replica credentials), `{tenant}/s3` per consumer (`seaweedfs_bucket`), `backup/s3-contabo` for the pull mirrors.
5. **Ansible adapter + vars:** `roles/seaweedfs` (`defaults/main.yml`: pin, ports, volume sizing, SSE, offsite, mirrors; templates `s3.json.j2`, `security.toml.j2`, `master.toml.j2`, `replication.toml.j2`, `mirror.env.j2`); `service_scaffold` native-retire for the old units.
6. **Removal notes:** `playbooks/decommission-service.yml`; class A — `/data` (every bucket: PBS datastore, Loki, GitLab, Harbor, mailcow backups, mirrors, …) is the platform's object store; the ZFS dataset outlives the guest and the Contabo replica holds a copy.

## Notifications (services/0005)

1. **Transport:** none — SeaweedFS sends no mail.
2. **What is sent:** nothing.
3. **Alerting path:** Prometheus job `seaweedfs` (`:9327/metrics`, 118 families) + blackbox `https://s3.<domain>/` → Alertmanager → Discord/mail; `SeaweedFSVolumeSlotsLow` is a platform rule.
4. **Logs:** the three containers (server, admin console, offsite backup) → journald → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class A (`docs/backup.md`): `/data` is replicated one way, continuously, to the off-site bucket (`weed filer.backup`, SSE-encrypted objects, credentials from Vault); the node's second daily vzdump covers the dataset; the guest image in PBS (daily, ct 550) carries the configuration only (`/data` is excluded from the image on purpose — PBS itself lives in a bucket here). Restore = dataset (or replica pull) + play.
