# Changelog

All notable changes to ansible-platform are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [0.2.0](https://github.com/by-openclaw/ansible-platform/compare/v0.1.1...v0.2.0) (2026-06-02)


### Features

* **adguard:** prod AdGuard Home role + playbook ([#27](https://github.com/by-openclaw/ansible-platform/issues/27)) ([d4d91b6](https://github.com/by-openclaw/ansible-platform/commit/d4d91b6ee975c816f64595ce610511a6195320d0))
* **adguard:** prod AdGuard Home role + playbook ([#27](https://github.com/by-openclaw/ansible-platform/issues/27)) ([2cae9d2](https://github.com/by-openclaw/ansible-platform/commit/2cae9d2baaa1034b5ccdd3269c4c72f78a123153))
* **dns-chain:** phase 1 — Unbound → dnscrypt-proxy on loopback ([8776881](https://github.com/by-openclaw/ansible-platform/commit/8776881e97bbb3f6cdcd0a21babaf2a1fd31867d))
* **dns-chain:** phase 1 — wire Unbound forwarder to dnscrypt-proxy on loopback ([5cf1f8a](https://github.com/by-openclaw/ansible-platform/commit/5cf1f8ab0cd293297720c75bd300598443b45ffc))
* **fw:** enforce DNS-through-FW-only — block plain (53) + DoT (853) leaks ([7a3c659](https://github.com/by-openclaw/ansible-platform/commit/7a3c659722159a121b5c9d9ce71ffe256dcd71e8))
* **fw:** enforce DNS-through-FW-only — block plain (53) + DoT (853) leaks across all internal VLANs ([e6630f6](https://github.com/by-openclaw/ansible-platform/commit/e6630f6db5b1bed3f88798fae38a823d73b896c8))
* **inventory:** env is per-host — all current hosts env=prod ([968ba66](https://github.com/by-openclaw/ansible-platform/commit/968ba66b2af37f0742aec923a566a41ef65784b9))
* **opnsense-prod:** prod FW config + inventory via MVC API ([#25](https://github.com/by-openclaw/ansible-platform/issues/25)) ([b074df9](https://github.com/by-openclaw/ansible-platform/commit/b074df9a2a24486a210aeb497e578b3881041d8d))
* **opnsense-prod:** prod FW config + inventory via MVC API ([#25](https://github.com/by-openclaw/ansible-platform/issues/25)) ([d31105c](https://github.com/by-openclaw/ansible-platform/commit/d31105c75dfe0ebfff798524f56c1abf1450cc7c))
* **opnsense:** add encrypted vault, fix inventory SSH config ([ccab171](https://github.com/by-openclaw/ansible-platform/commit/ccab171e1d5e8b42c821883cee2f9fc00884e4d0))
* **opnsense:** add opnsense role + bootstrap playbook ([21aaf72](https://github.com/by-openclaw/ansible-platform/commit/21aaf72a95998822c1ee1c0dce64d779193a4824))
* **opnsense:** add qemu-agent bootstrap task ([2ce3302](https://github.com/by-openclaw/ansible-platform/commit/2ce3302026aa1e3e5e3c435ae199d23d68aa1723))
* **opnsense:** wire lib-opnsense Dnsmasq + radvd managers, scaffold catalog ([8f2b54d](https://github.com/by-openclaw/ansible-platform/commit/8f2b54d37fe0d5d6578b34cc4fb38eb003fa6cd3))
* **opnsense:** wire lib-opnsense Dnsmasq + radvd managers, scaffold catalog ([eb501d4](https://github.com/by-openclaw/ansible-platform/commit/eb501d41fb2d0bc4576c8bf20e64b5424e9683c2))
* **opnsense:** WireGuard role — wg-byresearch-01, 3 peers, client config template ([518df47](https://github.com/by-openclaw/ansible-platform/commit/518df47d683a09939128ae32fdb3d34af1559c06))
* **opnsense:** WireGuard role + subnet renumber 10.100→10.99 ([6f98cba](https://github.com/by-openclaw/ansible-platform/commit/6f98cba37a9fe00f690a79cf232fc8c4533b5348))
* **test:** align catalog to ADR addressing + live FW interface map ([112c6af](https://github.com/by-openclaw/ansible-platform/commit/112c6afccae392489c57706bdf15a22a6fb5540f))
* **test:** align catalog to ADR addressing + live FW interface map ([9926194](https://github.com/by-openclaw/ansible-platform/commit/992619469050b05700d8411461687b20bca046a0))
* **validation:** FW + in-LXC validation harnesses ([bdd9917](https://github.com/by-openclaw/ansible-platform/commit/bdd9917b6c84fe118850b478700ed934897159fb))
* **validation:** FW + in-LXC validation harnesses ([6942048](https://github.com/by-openclaw/ansible-platform/commit/6942048e296948c3c28fa4819ea7a04ff1c031f5))


### Bug Fixes

* **adguard:** correct lego DNS-01 propagation flag for lego 4.21 ([ad07130](https://github.com/by-openclaw/ansible-platform/commit/ad071304d549ec6d8daa065bda7744fc25c8f00f))
* **adguard:** make role deploy cleanly on a fresh debian-12-cloud VM ([854d496](https://github.com/by-openclaw/ansible-platform/commit/854d49607864de4841a41c145f6e9e21a17ac4ae))
* **adguard:** make role deploy cleanly on fresh debian-12-cloud VM ([4d8c007](https://github.com/by-openclaw/ansible-platform/commit/4d8c00746487ec689faaf750182a70e5815ae24c))
* **agents:** link to doc-platform-core for agent contract files ([f9d8556](https://github.com/by-openclaw/ansible-platform/commit/f9d8556c7a83f1b042694f7ea56c7ce0478a59af))
* **agents:** remove unreachable OPERATING-STANDARD.md link ([df334df](https://github.com/by-openclaw/ansible-platform/commit/df334df7fd651f40c5d6b3c4dd86646ab0c73d0d))
* **agents:** restore OPERATING-STANDARD reference as plain text ([e6b38ee](https://github.com/by-openclaw/ansible-platform/commit/e6b38ee46837a3205041b1403229ce0e4cd3fb94))
* **ci:** allow platform-wide service accounts in naming check ([3239633](https://github.com/by-openclaw/ansible-platform/commit/3239633d7a1aa5726b20e529d7f4e2ee0b58b173))
* **ci:** naming-check exempts node-named inventory dirs ([a81e55d](https://github.com/by-openclaw/ansible-platform/commit/a81e55d3265cffb99d3f3f83effc4f54de77f5f1))
* **ci:** naming-check exempts node-named inventory dirs ([62d65a3](https://github.com/by-openclaw/ansible-platform/commit/62d65a31db4db0e3d05aa3fda8f463e909775ea1))
* **dns-chain:** keep unbound.forwarding.enabled=0 — recipe was misleading ([467126d](https://github.com/by-openclaw/ansible-platform/commit/467126d0c2e79a1df9dc37bb0d5d130e7edb4d8f))
* **fw:** align DNS-enforcement gateway aliases to ADR addressing ([8e1af30](https://github.com/by-openclaw/ansible-platform/commit/8e1af30a9dc75e5365e162ba1110dcc0d6415271))
* **fw:** radvd interface translation + empty Base6Interface ([0b04f2d](https://github.com/by-openclaw/ansible-platform/commit/0b04f2dcc2c1d809a4b53810ac28247ee6f6fbe0))
* **fw:** radvd interface translation + empty Base6Interface ([2266356](https://github.com/by-openclaw/ansible-platform/commit/226635613d6c121689a4b9f676be1b6c7fe8c001))
* **fw:** radvd mode stateless→unmanaged — stop DHCPv6 info-requests on test VLANs ([571b7a5](https://github.com/by-openclaw/ansible-platform/commit/571b7a5aacce55a84a314f99a7d21ff97d06e5b8))
* **fw:** radvd mode stateless→unmanaged to stop DHCPv6 info-requests ([78a4610](https://github.com/by-openclaw/ansible-platform/commit/78a4610a5fd5d83700b157aa0aeb28bc4e157f03))
* **inventory:** add explicit env tier to group_vars per ADR-0012 ([6b2c166](https://github.com/by-openclaw/ansible-platform/commit/6b2c1663f702a6f5f4a7dc65febb5d6b6e6d5f50))
* **opnsense:** aliases via collection, rules via uri, tunnel via async ([b164e54](https://github.com/by-openclaw/ansible-platform/commit/b164e54f9715440368e6ba12ebd107cc81cca514))
* **opnsense:** drop alias_ prefix from alias names — redundant by context ([65e541a](https://github.com/by-openclaw/ansible-platform/commit/65e541ab6eace330db9969973929c0ee9f2380af))
* **opnsense:** remove poc from hostname — vm-opnsense-01 per ADR-0010 ([1603f3f](https://github.com/by-openclaw/ansible-platform/commit/1603f3f9ffcb418c48b3cf713438c1c13868b47a))
* **opnsense:** rewrite firewall aliases+rules tasks — uri module, SSH tunnel ([3646086](https://github.com/by-openclaw/ansible-platform/commit/3646086edb396ba11a3fca2ce1254e355fed01a4))
* **opnsense:** wireguard tasks — bypass collection bugs with direct API calls ([d9efbe7](https://github.com/by-openclaw/ansible-platform/commit/d9efbe7b93590704d29873b385b63811b204d862))
* **prod-inventory:** adguard uses no-pass automation key + ProxyCommand jump ([#25](https://github.com/by-openclaw/ansible-platform/issues/25)) ([dfa3cb5](https://github.com/by-openclaw/ansible-platform/commit/dfa3cb5e1dcb0317dce6fcb10e29911bc804780b))
* **wireguard:** renumber tunnel subnet 10.100.0.0/24 → 10.99.0.0/24 ([d2c8661](https://github.com/by-openclaw/ansible-platform/commit/d2c86614bb4aca9e217cf4430a57ed390453adfd))

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
