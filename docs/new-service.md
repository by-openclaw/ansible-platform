# Golden path — adding a new platform service

Every new service is **born compliant** by composing the platform's concern-roles
through `roles/service_scaffold`, plus three one-line central registrations. This
is the checklist; the scaffold role does the per-host work, and asserts the
central bits are present so nothing ships half-wired.

## 1. Provision the guest (Terraform)

Add `environments/prod/svc-<name>.tf` in `infra-terraform-proxmox` from the
`lxc-cloudinit` module (VMID, SVC IP, VLAN, cores/mem/disk). `terraform apply`.
Then add the host to `inventories/prod/hosts.yml` under the right group.

## 2. Write the service role

`roles/<name>/` installs the app itself (pinned image — never `:latest`), then
**includes `service_scaffold`** with the contract:

```yaml
- name: "<Name> | Scaffold the platform concerns"
  ansible.builtin.include_role:
    name: service_scaffold
  vars:
    service_scaffold_def:
      name: <name>                         # naming/0002 §3 {function}
      fqdn: "<name>.{{ platform_domain }}"
      backend_url: "http://<svc-ip>:<port>"
      exposure: internal                   # internal (VPN) | public
      mailbox: true                        # {name}@{domain} rx/tx + adm delegate
      db: postgres                         # none | postgres
      s3_bucket: ""                        # "" | <bucket>
      vault_secrets:
        - path: "prod/<name>/app"
          init: { admin_token: "{{ lookup('community.general.random_string', length=40, special=false) }}" }
      logrotate:
        - { name: <name>, paths: ["/var/log/<name>/*.log"], rotate: 14 }
      sso_slug: <name>                     # asserted present in authentik_oidc_apps
```

The scaffold composes, in order: **Postgres DB** (if `db: postgres`) → **S3
bucket** (if `s3_bucket`) → **Vault secrets** → **mailbox** → **Traefik route**
→ **logrotate** → **central-registration assertions**.

## 3. Three central registrations (one edit each)

These live in shared data files — the scaffold **asserts** them:

- **SSO** — add an entry to `authentik_oidc_apps` in
  `roles/authentik/defaults/main.yml` (slug, launch_url, group, redirect_uris,
  secret_file). Run `playbooks/authentik.yml`. *(Skip only for a service with no
  human UI; then leave `sso_slug` empty.)*
- **Firewall** — add the port alias + the DMZ→SVC / edge rule to the OPNsense
  catalog in `inventories/prod/group_vars/opnsense.yml` (lib-first; never manual
  drift). Apply scoped: `-e '{"opn_fw_only": ["<name>"]}'`.
- **Audit** — add a `contract_audit` row (id/desc/probe/expect/groups) in
  `roles/contract_audit/defaults/main.yml` so the service's key property is
  enforced fleet-wide.

## 4. Mailbox fan-out

Add `- { svc: <name> }` to `playbooks/mailboxes.yml` (the scaffold provisions the
box; the fan-out keeps the platform-wide list authoritative).

## 5. Prove it

- `ansible-playbook playbooks/<name>.yml` → rerun **`changed=0`** (idempotent).
- **Integration test**, not smoke: read the service logs / real protocol, not a
  200. Confirm the daemon is healthy and stable.
- Edge check from **inside the fabric** (the controller can't reach DMZ 443).
- `playbooks/contract-audit.yml` still **22/22 fails=[]**.
- `playbooks/secrets-validate.yml` if it has Vault-backed creds.

## 6. Document

`roles/<name>/README.md` + `docs/` entry (setup / backup / runbook), per
INF-41. A stateful service needs `docs/backup.md` and a verified first backup
before it counts as production.

---

**Why the scaffold:** SSO, mailbox, Vault, TLS/exposure, backup, hardening and
audit are not per-service inventions — they are platform contracts. The scaffold
makes them the default so a new service inherits the baseline instead of being
hand-assembled and drifting.

## Host firewall (ufw) — every guest, every role

The hardening baseline installs and enables ufw with SSH only (`hardening_ufw_allowed_ports`). A role
that has **native listeners** declares its ports with `roles/host_firewall` (rule list in the role's
defaults, sources = `platform_trusted_cidrs`, public entries without `from`); Docker-published ports
need no rule (Docker's DNAT precedes ufw INPUT) and `roles/docker` already lets the container networks
reach the host (hairpin to published ports). Order on a new guest: service play first (rules are stored
while ufw is inactive) → hardening (enables) → baseline roles → rerun changed=0 → contract-audit
(SEC-21 checks `ufw status` = active). Never enable ufw before the service's rules exist.
