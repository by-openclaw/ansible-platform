# role: opnsense_api_bootstrap

Mint the **svc-ansible** OPNsense API identity **through the MVC API**
(`POST auth/user/add_api_key/{user}`) and store the token in **Vault** — no GUI
click, no static API key baked into the seed. Get-or-mint + idempotent.

## Why

The seed does **not** carry an svc-ansible API key. A Terraform+seed rebuild
needs a hands-off way to obtain one. This role mints it via MVC and collects it
into Vault, so every later FW play reads a Vault-owned token.

## The genesis (chicken-and-egg) credential

The *first* API call after a rebuild needs an existing admin key. That is the
**one seeded credential** — a break-glass admin (`root` / `oob-admin`) whose key
is provided via `opnsense_api_bootstrap_genesis_file` (a secret file with
`.fields.key` / `.fields.secret`) or `_genesis_key`/`_genesis_secret`.
svc-ansible's own token is **never** seeded — it is minted here.

On a **seeded** FW the svc-ansible user + `admins` membership already exist (from
the seed), so this role is effectively **mint-only**. On a **bare** FW it also
creates the user (random password — real auth is the API key + SSH keys) and adds
it to `admins`.

## Flow (idempotent)

1. `vault_login` → read `secret/{{ vault_path }}`. **If present → reuse (noop).**
2. Else mint: ensure user → ensure `admins` membership (members/privs preserved;
   sent as **CSV**, arrays 500) → `add_api_key` → **write to Vault** → publish
   `opn_key`/`opn_secret` → optional 0600 DR mirror in the secret folder.

## Key variables (see `defaults/main.yml`)

| var | default | note |
|---|---|---|
| `opnsense_api_bootstrap_host` | `ansible_host` | target FW |
| `opnsense_api_bootstrap_user` | `svc-ansible-prod` | identity to mint |
| `opnsense_api_bootstrap_genesis_file` | `""` | break-glass admin secret file |
| `opnsense_api_bootstrap_env` | `platform_env` (→ `prod`) | env segment of the KV path |
| `opnsense_api_bootstrap_vault_path` | `{platform_env}/opnsense/api` | KV v2 path — **same path `opnsense_api_creds` reads** |
| `opnsense_api_bootstrap_collect_file` | `.../net-opnsense-{env}-svc-ansible.json` | 0600 DR mirror, same name the `vault_kv_map` sync uses ("" to skip) |

## Example

```yaml
- hosts: opnsense
  gather_facts: false
  roles:
    - role: opnsense_api_bootstrap
      vars:
        platform_env: prod            # → writes secret/prod/opnsense/api
        opnsense_api_bootstrap_genesis_file: >-
          {{ lookup('env','HOME') }}/.openclaw/workspace/infra/secrets/fabric/net-opnsense-prod-oob-admin.json
```

## Verified (live, 2026-09-06, OPNsense 26.7 CE)

| Path | Target | Result |
|---|---|---|
| **reuse** | seeded test FW, `secret/test/opnsense/api` present | *reused from Vault (noop)*, `changed=0`; published token → `auth/user/search` **HTTP 200** |
| **mint** | lab FW, empty scratch path | *MINTED via MVC + stored in Vault*, `changed=1` (the Vault write); 2nd on-box key confirmed |
| **idempotent** | lab FW, 2nd run | *reused (noop, verified HTTP 200)*, `changed=0` |
| **rotate** | lab FW, Vault holds a stale/bogus token (= FW rebuilt/reseeded) | *ROTATED — re-minted via MVC + stored* (new KV v2 version, history kept), `changed=1`, new token **HTTP 200** |
| **check mode** | `--check` with token absent | reports *would mint*, makes no change |

Run from the controller (`hosts: localhost`, set `opnsense_api_bootstrap_host`) —
the FW needs no SSH/Python for this role. Vault auth = `ansible-deploy` AppRole
(`vault_deploy_auth = approle`).

> Uses `ansible.builtin.uri` for the MVC calls (consistent with `roles/opnsense`).
> Migrates to the lib-opnsense Ansible collection when the OPNsense lib-loop lands.

## Forced rotation (SEC-09)

```bash
# rotate even though the current token works (schedule, or after an exposure)
ansible-playbook -i inventories/<env> playbooks/opnsense-api-bootstrap.yml -e opnsense_api_bootstrap_force_rotate=true
```
