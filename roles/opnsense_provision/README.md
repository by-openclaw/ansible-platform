# roles/opnsense_provision

Builds an OPNsense firewall VM from its seed profile (`infra-terraform-proxmox/modules/vm-opnsense/seed/seeds/<fw>.json`):
images on the node → VM from the profile's hardware truth → `config.xml` handed to the boot importer →
the appliance answers. Called by `playbooks/opnsense-provision.yml` and as stage 0 of
`playbooks/opnsense-build.yml`. Full contract: `docs/services/opnsense.md` §7.

| Variable | Meaning |
|---|---|
| `opnsense_provision_fw` | seed profile name (required) |
| `opnsense_provision_recreate` | destroy and rebuild an existing VM (prod also needs `opnsense_provision_confirm_prod`) |
| `opnsense_provision_state` | `present` (default) or `absent` — see below |
| `opnsense_provision_archive_storage` | vzdump store for the decommission archive (`poc-backup`) |

## Decommission (`opnsense_provision_state: absent`)

`-e opnsense_provision_state=absent` archives the VM with a final `vzdump` to
`opnsense_provision_archive_storage` (the NAS store), then destroys it — never a delete without the
archive, and idempotent (an absent VM is only reported). A prod profile is refused. Everything that
re-creates the firewall later stays in place: the seed profile, the ISP address allocation
(`ISP-ALLOCATION.md`), `inventories/test`, the Vault paths. Used on 2026-09-22 to retire the two lab
firewalls while keeping the Telenet address for future image validation.
