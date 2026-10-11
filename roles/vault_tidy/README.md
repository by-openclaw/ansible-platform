# vault_tidy

One document per secret. Retires, by data, the Vault documents and fields nothing reads any more.

- **Documents** (`platform_vault_retired_documents`): archived with the routine of
  `roles/service_decommission` — copied under `archive/`, the copy read back and compared, then
  the original removed. Nothing is deleted without a verified copy.
- **Fields** (`platform_vault_retired_fields`): removed from their document; the write only goes
  through if the document did not change in the meantime, and the result is read back. The
  previous version of the document stays in the store's version history.
- **Guard** (`same_as`): an entry names where the same value lives now. The run compares the
  two values in memory and refuses to retire anything that differs — the last copy of a secret
  is never removed.

- **Restore** (`platform_vault_restored_documents`): a document is brought back from `archive/`
  to its live place when it was retired by mistake or is needed again — the copy is read back
  and compared before the archived one is removed.

Entries stay in the inventory after they have been applied: they are the record of what was
retired and why. `playbooks/vault-tidy.yml --check` reads, compares and says what it would do.
