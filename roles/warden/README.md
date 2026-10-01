# role: warden (Vault auto-unseal)

Warden on `lxc-warden-01`: holds **3 of 5** unseal shares (`/etc/warden/unseal.json`) and auto-unseals Vault on cold start (`warden-coldstart.{service,timer}`). The engine is a one-shot container (`warden_image`, an Ansible execution environment): created at install (the image is local — a cold start needs no registry), each timer run is `docker start --attach warden-coldstart`, which runs the local playbook once. Proven by a controlled seal→heal drill (<60s).

- Shares sourced once from the controller `vault-init.json`; the controller copies are purged only on the USER's explicit go (print-kit).
- Probes `warden_probes` gate the unseal.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/warden.yml`

## Backup & restore

Class **A** (guest image); the shares are the sensitive state — also in the print-kit. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `systemctl status warden-coldstart.timer`; after a Vault restart, `vault status` shows `Sealed false` within a minute.
- Common: unseal not firing → timer inactive or share file missing.
