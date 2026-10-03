# step-ca (internal CA) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: step-ca`). Role `roles/step_ca`, play `playbooks/step-ca.yml`, guest `lxc-stepca-01`. Audit: [`docs/audits/step-ca-2026-10-03.md`](../audits/step-ca-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `security/0004` (CA choice: internal names → step-ca, public FQDNs → Let's Encrypt); no user interface (`sso: none`). Certificates are requested through the provisioners: `acme` (ACME for services) and the JWK provisioner `admin@<domain>` (operators, with the provisioner password).
2. **Authentik application:** none.
3. **Access model:** the ACME provisioner is reachable from the platform networks only (route internal-only + host firewall); the JWK provisioner needs the key password; the CA runs as the unprivileged `step` user. The root certificate is distributed to every host's trust store by the hardening baseline.
4. **Vault paths:** `secret/{env}/step-ca/ca-password` (the password protecting the root and intermediate keys), `step-ca/root-fingerprint` (the escrow the role keeps equal to the live root).
5. **Ansible adapter + vars:** `roles/step_ca` (`defaults/main.yml`: pin `step_ca_image`, names, provisioner; `tasks/main.yml`: password get-or-create, the state volume, the container + route + mailbox through `service_scaffold`, the health wait, the root fingerprint escrow).
6. **Removal notes:** not removable while certificates it issued are in use; the CA state (keys, badger database) lives in the `step-ca-data` volume → the PBS guest image; a rebuilt CA = a new root (every trust store changes) unless the volume is restored.

## Notifications (services/0005)

1. **Transport:** SMTP through the `step-ca@<domain>` mailbox (minted by the scaffold) — unused by the CA itself today.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus `node` + `cadvisor` + the blackbox probe of `https://ca.<domain>/health` → Alertmanager → Discord/mail; certificate-expiry alerts come from the consumers' probes.
4. **Logs:** the container on journald (every signing request) → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class A (`docs/backup.md`): the CA state volume (root + intermediate keys encrypted with the Vault-held password, the certificate database) in the PBS guest image (encrypted, replicated off-site); the password in Vault. Restore = PBS volume + play (the fingerprint escrow proves the same root came back).
