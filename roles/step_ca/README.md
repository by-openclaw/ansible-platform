# role: step-ca (internal CA)

smallstep **step-ca 0.28.4** on `lxc-stepca-01` (`10.1.3.192`, `ca.<domain>` VPN-only). **`BY-RESEARCH Internal CA`** (name derived from `platform_domain`). SCOPE: **internal device certificates only** (802.1X NAC, mTLS between devices, machine identity) — Let's Encrypt stays the issuer for all public/edge/service TLS.

- Auto-init on an empty volume via `DOCKER_STEPCA_INIT_*`; init password mounted at `/run/init-pw` (**never under `/home/step`** — it clobbers the key dir).
- Vault: `prod/step-ca/ca-password` (root+intermediate key password) and `prod/step-ca/root` (fingerprint, URL). ACME + JWK (`admin@<domain>`) provisioners.
- Born through `service_scaffold` (mailbox `step-ca@`, route, logrotate).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/step-ca.yml`

## Backup & restore

Class **A ⚠**: `step-ca-data` volume in PBS **plus** the Vault password = the CA. Losing both means re-initialising a *new* CA (all issued certs orphaned). Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `https://<ip>:9000/health` 200; issue a test cert: `step ca certificate test.<domain> …`.
- Common: permission-denied on `intermediate_ca_key` → a file bind-mounted into `/home/step/secrets` (don't); `/dev/tty` error → init password not consumed.
