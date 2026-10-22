# Retired public keys

The public halves of SSH keys the platform no longer uses (owner's instruction 2026-10-15:
"purge keys not used"). They stay here so a key can still be recognised in a log or on a host,
and so the roles can remove them by key text wherever they are still accepted:

- `roles/pve_host` — root's keys on the Proxmox nodes (by name, never an exclusive write there);
- `roles/user-mgmt` — root's keys on every guest are an exclusive, declared list (empty);
- `roles/windows_guest` — `administrators_authorized_keys` is an exclusive, declared list.

The private halves were set aside on the controller (`playbooks/controller-files.yml
-e controller_files_area=keys -e controller_files_set_aside=true`) and are destroyed with
`-e controller_files_purge=true` on the owner's go. A key is never put back from here.

| File | Comment on the key | Where it was still accepted |
|---|---|---|
| `id_ed25519_by-systems.pub` | `by-systems@rune-vm` | root on 32 guests (inert: `PermitRootLogin no`), Administrator on the Windows guests, Terraform's first-boot list |
| `id_ed25519_rune.pub` | `rune@by-systems-rune-vm` | root on the first hypervisor and one guest; `ansible.cfg`'s former default key |
| `id_ed25519.pub` | the owner's early personal key | nowhere |

- `id_ed25519_rune_nopass.pub` — the Windows guests' keyless connection key (April 2026), replaced by `svc-rune-prod` on 2026-10-22 (PR #1020); Vault `prod/windows/ssh-key` archived.
