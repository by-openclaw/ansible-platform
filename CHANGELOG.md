# Changelog

All notable changes to ansible-platform are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

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
