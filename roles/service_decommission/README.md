# role: service_decommission

Force a retired service ABSENT, archive before destroy. Run:
`ansible-playbook playbooks/decommission-service.yml -e decommission_target=<name>`
(`--check` first: it reads everything and removes nothing).

The footprint comes from the platform service catalog (`group_vars/all/services.yml`), or from
`decommission_catalog` for the leftovers of a service whose role is already gone. Each component
is optional and skipped when already absent:

| Component | What happens | How |
| --- | --- | --- |
| `db` | `pg_dump` (custom format) on the PostgreSQL leader, read back with `pg_restore -l`, fetched to the controller archive (`decommission_dump_dir`), removed from the leader; then `DROP DATABASE` and `DROP ROLE` | a transient systemd unit (`systemd-run --wait`) sends the container's output to a root-only file — no shell redirect; nothing is dropped when the dump does not read back as this database's archive |
| `secrets` | each Vault KV v2 secret is copied under `archive/` (a legacy fabric name under `fabric/archive/`), the copy is read back and compared, then the original is removed | Vault's HTTP API from the Vault host, with the deploy identity (`tasks/vault_archive_one.yml`) |
| `s3_identity`, `s3_bucket` | the SeaweedFS identity and its keys are removed; the bucket only when it is empty (the run fails otherwise, nothing removed) | `weed shell` reading its commands on standard input |
| `traefik_route` | the route is withdrawn | `roles/traefik_route` with `state: absent` |
| `authentik_app`, `authentik_group` | the application, its provider and (optionally) a group are deleted | Authentik's REST API on its host; refused while the application is still declared in `group_vars/all/sso.yml` (the blueprints would create it again within the hour) |
| `crowdsec_machine` | the machine registration is deleted | `cscli` in the LAPI's container |
| `guest`, `split_dns` | reported, not removed | Terraform (`infra-terraform-proxmox`) and the firewall catalog own them |

No program is staged on a host and no token is written to a file. The two programs this role
used to stage are kept under `_archive/` for reference; the tasks remove their former copies
from `/tmp` on the Vault and Authentik hosts.

Settings: `defaults/main.yml` (where each component lives, the dump directory on the leader,
Vault's KV mount, Authentik's API address and token path).
