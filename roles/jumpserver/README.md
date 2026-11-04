# role: jumpserver (bastion)

JumpServer CE **v4.10.19** on `lxc-jumpserver-01` (per-container, no compose). Authentik OIDC, bundled PG16+Redis7 (named volumes), assets = the fleet with rune-key accounts, session replays → S3 (`seaweedfs`), CrowdSec agent. VPN-only via Traefik.

- Windows guests (RDP): three accounts each — `<org>` (break-glass admin), `<org>-user` (user session) and the built-in `Administrator` (the session that signs in at boot, where Cerebrum runs; its own password per guest, `<tier>/windows/<host>/administrator`). The login test covers `<org>` and `Administrator`.
- Vault: `prod/jumpserver/{app,oidc,smtp}`; own mailbox `jumpserver@`.
- Containers ride journald (recreated 2026-09-02).

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/jumpserver.yml`

## Backup & restore

Class **A + C**: bundled PG/Redis volumes in PBS; recordings offsite via S3. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `docker ps` (7 containers), edge `/api/health/` 200.
- Restart: rerun the play (recreates on config change).
- Common: OIDC group mapping is limited in CE — access is by Authentik group + local role.
