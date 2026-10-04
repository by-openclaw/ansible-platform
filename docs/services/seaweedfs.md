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

## Rotation of the SSE-S3 key (security/0001 SEC-09)

`ansible-playbook playbooks/seaweedfs.yml -e seaweedfs_sse_rotate=true` (`roles/seaweedfs/tasks/rotate_sse.yml`). It restarts the S3 gateway and the offsite replication once: announce it, outside the backup window and not during a datastore verification.

- **What the key protects:** only objects written with the S3 server-side-encryption header (or into a bucket that encrypts by default). Each carries its own data key, wrapped by the key-encryption key in use when it was written; SeaweedFS holds one such key and has no rotation of its own. With another key such an object answers 500 on GET, and the offsite replication would retry it for ever.
- **What the rotation does:** it refuses to run while a bucket encrypts by default or an object exists under a prefix that is written with the header (`platform_sse_written_prefixes`, looked for in every bucket); it proves its own read-back test with the current key; it writes a new key to Vault (the former one stays in the version history); the role renders it and restarts the two processes that hold it; then an object written with the header must read back, the offsite replication must run, and the gateway's log must show no "failed to decrypt DEK".
- **If objects under the former key exist:** they must be copied under the new key first — a second, temporary gateway started with the former key on the same filer serves them for reading, and each is written again through the gateway that holds the new key. Not automated: no such object existed at the first rotation (inventory of 2026-10-04: 21 buckets, none encrypting by default, no object under `leavers/`, no SSE header on the sampled objects of each bucket).
