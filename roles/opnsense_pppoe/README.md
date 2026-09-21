# opnsense_pppoe — the ISP PPPoE credential, Vault-first

PPP devices sit on a legacy OPNsense page with no API. This role makes the credential's life cycle
code: **Vault is the store of record (raw value)**, the appliance's `config.xml` holds what OPNsense
reads (`base64`), the seed renders the same at a rebuild, and the break-glass fallback file is
refreshed *from* Vault — never the other way round.

| Task file | Runs on | Does |
|---|---|---|
| `vault.yml` | Vault host | reads the secret + custom metadata; rotation (new value), one-time normalisation (`opnsense_pppoe_normalize`) or converge; one new KV version at most; metadata `format=raw`, `rotated_at`, `rotated_by`, `reason`, `version_stamped` (a version written through the Vault UI gets its trail completed as `rotation-external`); hands the raw value over |
| `apply.yml` | firewall (SSH + wheel sudo) | refuses cleanly when the appliance grants no sudo (seed-owned `sudo_allow_wheel`, window #379); surgical `<password>` edit inside `<ppps>` (attributes kept, dated copy beside it); `configctl interface reconfigure <slot>` only on change |
| `verify.yml` | firewall (API) | polls `routes/gateway/status` until the catalog's v4 AND v6 gateways are back; interface overview (IPv4 + global IPv6 present) |
| `fallback.yml` | controller | refreshes the file `roles/opnsense_provision` reads when Vault is unreachable |

Catalog: `opn_wan_pppoe: {interface, ports, gateway_v4, gateway_v6}`, `opn_ssh_port`. Playbook:
`playbooks/opnsense-pppoe-rotate.yml` (hidden prompt). Rotation day: ISP portal first, playbook right
after — the running session keeps its authentication until it re-dials.
