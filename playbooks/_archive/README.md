# Archived playbooks (never delete — archive)

Superseded on 2026-09-07. Not wired anywhere; kept for history.

| Playbook | Superseded by |
|---|---|
| `opnsense-bootstrap.yml` (hostname + WAN static IP via raw `uri`, vault.yml file) | the seed pipeline (`build-seed.py` renders identity + interfaces; secrets at render time — SVC-49) |
| `opnsense-identity.yml` (by-research break-glass, svc-ansible-prod user + one-time API key to a local file, seed-bootstrap fields) | seed baseline (users `by-research`, `svc-ansible-prod`, `oob-admin` genesis) + `roles/opnsense_api_bootstrap` / `playbooks/opnsense-api-bootstrap.yml` (get-or-mint → Vault `{env}/opnsense/api`, rotate-on-stale, lib-first via `by_systems.opnsense`) |
