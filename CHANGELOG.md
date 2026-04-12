# Changelog

All notable changes to ansible-platform are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

### Added
- `roles/opnsense/tasks/wireguard.yml` — WireGuard server + 3 peers via `puzzle.opnsense` collection (issue #88)
- `roles/opnsense/templates/wireguard-client.conf.j2` — client config generator for all peers
- `files/client-configs/` — output directory for generated client configs (gitignored)

### Changed
- `roles/opnsense/defaults/main.yml` — WireGuard vars updated: instance name `wg-byresearch-01`, vault key names aligned to convention (`vault_opnsense_wg_byresearch01_*`, `vault_opnsense_wg_peer_*`)
- `roles/opnsense/tasks/wireguard.yml` — full rewrite: firewall rule, reconfigure call, client config generation added

---

## [0.1.1](https://github.com/by-openclaw/ansible-platform/compare/v0.1.0...v0.1.1) (2026-03-30)


### Bug Fixes

* correct pull_request trigger in project-board-sync workflow ([bde2dca](https://github.com/by-openclaw/ansible-platform/commit/bde2dcae2bb2e163389155a66f6d893761637c7e))

## [0.1.0] — 2026-03-28

### Added
- Initial repository structure
- Role: `hardening`
  - `sshd`: full sshd_config replacement — port 22222 only, key-only auth, break-glass pattern
  - `fail2ban`: SSH jail on port 22222, optional Proxmox web jail
  - `ufw`: default deny, allow by network/port
  - `email-relay`: postfix satellite relay (optional)
- Inventory: `poc` — srv-proxmox-poc-01, vm-debian-bootstrap-test-01
- Playbook: `hardening.yml`, `site.yml`
- CLAUDE.md, AGENTS.md, README.md

[0.1.0]: https://github.com/by-openclaw/ansible-platform/releases/tag/v0.1.0
