# warden (cold-start reconciler) — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: warden`). Role `roles/warden`, play `playbooks/warden.yml`, guest `lxc-warden-01` — a dedicated guest with no other workload. Audit: [`docs/audits/warden-2026-10-03.md`](../audits/warden-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `security/0001` (secrets) — the approved single-host model: the warden is the machine trust point for Vault's unseal; the printed kit is the disaster-recovery path. No user interface (`sso: none`).
2. **Authentik application:** none.
3. **Access model:** nobody logs into a warden service; host access = the SSH baseline (admins). The one-shot container reads the unseal shares (a threshold's worth, `0600 root`) and sends them to Vault's API over TLS in the request body (never on a command line); it holds no Vault token and no other credential.
4. **Vault paths:** none read at runtime (it runs while Vault is sealed); the shares were seeded once from the bootstrap material.
5. **Ansible adapter + vars:** `roles/warden` (`defaults/main.yml`: the execution-environment image pin `warden_ee_version`, threshold, probes, optional Discord webhook; `tasks/main.yml`: the share file (seeded once), the local cold-start playbook, the container (created, started by the timer), the `warden-coldstart` host job: 30 s after boot, then every 5 minutes).
6. **Removal notes:** removing the warden makes every cold start a manual unseal (printed kit); class D — nothing to archive (the shares exist in the kit).

## Notifications (services/0005)

1. **Transport:** the journal (and Discord when `warden_discord_webhook` is set — empty today).
2. **What is sent:** the outcome of every cold-start run (unseal performed or not needed, probe results).
3. **Alerting path:** a Vault that stays sealed fails the `/v1/sys/health` probe → Alertmanager → Discord/mail; `node` + `cadvisor` for the guest.
4. **Logs:** the unit and the container on journald → promtail → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class D (`docs/backup.md`): configuration = this role; the share file is re-seeded from the kit; the guest image in PBS is a convenience (encrypted). Restore = re-run `warden.yml` with the bootstrap material present.
