# Role: vault_backup

Automated **Vault raft snapshots** — the correct disaster-recovery mechanism for
Vault. A raft snapshot is one consistent, portable file that restores the entire
Vault (all KV secrets, policies, mounts, auth) into a fresh server.

## What it does
- Writes a low-privilege `snapshot` policy + a **self-renewing periodic token**
  (snapshot-read only — never the root token) stored `0600` on the vault host.
- Installs `/usr/local/bin/vault-snapshot.sh` + a **daily systemd timer**
  (`vault-snapshot.timer`, default `02:15`, before the `03:30` PBS job).
- Snapshots land in `{{ vault_backup_dir }}` (`/var/lib/vault/snapshots`), keeping
  the newest `vault_backup_keep` (14). That dir is inside the vault LXC, so every
  snapshot is **also carried by the node's vzdump jobs → Synology (NFS) + SeaweedFS
  (S3)** with no extra S3 tooling here.
- The `playbooks/vault-backup.yml` play also **pulls the newest snapshot to the
  controller** store (`infra/secrets/backups/vault/`) for an immediate off-host copy.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/vault-backup.yml`

## The three copies of a snapshot
1. On the vault host (`/var/lib/vault/snapshots`, last 14).
2. On Synology **and** SeaweedFS S3 (via vzdump of the vault LXC).
3. On the controller (`infra/secrets/backups/vault/`, newest only).

## Restore (rebuild Vault from a snapshot)
Prereqs you must ALSO have (kept in `infra/secrets/vault-init.json`, and now
mirrored into Vault itself via `secrets-to-vault.yml` — but for a *full* Vault
loss you need the **controller/offline copy**): the **unseal keys** and a
**root/recovery token**. Without the unseal keys a restored Vault cannot be unsealed.

```bash
# 1. Stand up a fresh, INITIALISED + UNSEALED Vault (same version), e.g. re-run the
#    vault role, or restore the LXC from vzdump.
# 2. Copy a snapshot in and restore it (this REPLACES all data):
docker cp vault-YYYYMMDDThhmmssZ.snap vault:/tmp/restore.snap
docker exec -e VAULT_TOKEN=<root-or-recovery-token> vault \
    vault operator raft snapshot restore -force /tmp/restore.snap
# 3. If the restored data was sealed with different keys, unseal with the ORIGINAL
#    unseal keys from vault-init.json. Verify: `vault kv get secret/fabric/pbs-encryption-key`.
```

> **DR ordering:** Vault holds the PBS encryption key (and every other secret).
> A snapshot on S3/NFS is only useful if you can unseal the restored Vault — so
> `vault-init.json` (unseal keys) MUST live somewhere off the platform (password
> manager / offline). Everything else recovers from the snapshot.

## Verify the timer
```bash
systemctl list-timers vault-snapshot.timer
ls -lt /var/lib/vault/snapshots/
```
