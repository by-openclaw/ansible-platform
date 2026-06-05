# Changelog

All notable changes to ansible-platform are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [0.3.0](https://github.com/by-openclaw/ansible-platform/compare/v0.2.0...v0.3.0) (2026-06-05)


### Features

* FW all-services health gate — 22/23 green, reporting the lone red ([#37](https://github.com/by-openclaw/ansible-platform/issues/37)) ([a579d36](https://github.com/by-openclaw/ansible-platform/commit/a579d36a0828468a8fb40bf3a162063aff5fd5dc))
* **fw:** add --only section scoping to fw_apply_direct ([2cd04ae](https://github.com/by-openclaw/ansible-platform/commit/2cd04ae96182d5cf1e0f0f214cdb73241f33fa30)), closes [#54](https://github.com/by-openclaw/ansible-platform/issues/54)
* **fw:** chrony/NTP enforcement — block external NTP, declare DHCP option 42 ([8240cd5](https://github.com/by-openclaw/ansible-platform/commit/8240cd54724175a85d3a4cce63f9cd0b9e4354c2)), closes [#56](https://github.com/by-openclaw/ansible-platform/issues/56) [#85](https://github.com/by-openclaw/ansible-platform/issues/85)
* **fw:** chrony/NTP enforcement — force all VLANs to FW chrony + block external NTP ([c49b0d7](https://github.com/by-openclaw/ansible-platform/commit/c49b0d70fa76483df09d442536eb052ba48aeb42))
* **fw:** idempotent firewall aliases + filter-rules baseline on prod + --only scoping ([c064cab](https://github.com/by-openclaw/ansible-platform/commit/c064cab9323a984692cd779d24ec0e18fbad9945))
* **opnsense:** activate plugin services via API reconfigure ([#43](https://github.com/by-openclaw/ansible-platform/issues/43)) ([8821e7c](https://github.com/by-openclaw/ansible-platform/commit/8821e7c16a6c80547699c1b3a385937c59317270))
* **opnsense:** activate plugin services via API reconfigure ([#43](https://github.com/by-openclaw/ansible-platform/issues/43)) ([c9c832f](https://github.com/by-openclaw/ansible-platform/commit/c9c832feb3b93f203d52ab549d5d41da94dd7fd8))
* **opnsense:** firmware upgrade + plugins via ansible ([#41](https://github.com/by-openclaw/ansible-platform/issues/41)) ([a0d6b2c](https://github.com/by-openclaw/ansible-platform/commit/a0d6b2c5c370bcfc1d8cab9ef1afb864bd630e15))
* **opnsense:** firmware upgrade + plugins via ansible ([#41](https://github.com/by-openclaw/ansible-platform/issues/41)) ([cd2aad0](https://github.com/by-openclaw/ansible-platform/commit/cd2aad04dc3c33bac80bf4a8eb303142634c8e36))
* **opnsense:** lldpd + chrony via API, gate seed-owned VLANs ([cedeef0](https://github.com/by-openclaw/ansible-platform/commit/cedeef00eacf182ea9522f6a95211a0bef1c9e45))
* **opnsense:** lldpd + chrony via API, gate seed-owned VLANs ([#45](https://github.com/by-openclaw/ansible-platform/issues/45)) ([49e4f3a](https://github.com/by-openclaw/ansible-platform/commit/49e4f3a51e6560f6563a6115ec9c8c46d78b8189))
* **opnsense:** Monit monitoring + email alerts via Resend ([#49](https://github.com/by-openclaw/ansible-platform/issues/49)) ([6f88b41](https://github.com/by-openclaw/ansible-platform/commit/6f88b4160e6e850754f9398c5a0e3ce635801f9f))
* **opnsense:** Monit monitoring + email alerts via Resend (idempotent) ([2082e3d](https://github.com/by-openclaw/ansible-platform/commit/2082e3dc7a862610cfe36d5df1ba991fcc561d66))
* **opnsense:** WAN gateway monitoring via MVC ([#39](https://github.com/by-openclaw/ansible-platform/issues/39)) ([8837309](https://github.com/by-openclaw/ansible-platform/commit/88373092d97fc48eb3894572316878b0de850d0a))
* **opnsense:** WAN gateway monitoring via MVC ([#39](https://github.com/by-openclaw/ansible-platform/issues/39)) ([84a4ef0](https://github.com/by-openclaw/ansible-platform/commit/84a4ef0b4422d2bce0215150c48c183cd2c3dd65))
* **opnsense:** WAN2 Telenet gateways via ansible ([#32](https://github.com/by-openclaw/ansible-platform/issues/32)) ([a52caea](https://github.com/by-openclaw/ansible-platform/commit/a52caeae39c690a7280f46ca6d7f52baade8fd41))
* **opnsense:** WAN2 Telenet gateways via ansible ([#32](https://github.com/by-openclaw/ansible-platform/issues/32)) — needs seed half ([8c5fe9e](https://github.com/by-openclaw/ansible-platform/commit/8c5fe9e565bbd6183be017b92393f6a29990b7a5))
* **scripts:** extend FW health gate to all services ([#37](https://github.com/by-openclaw/ansible-platform/issues/37)) ([41f7be3](https://github.com/by-openclaw/ansible-platform/commit/41f7be39406a4619beb86bc601bdfd267b98734d))
* **scripts:** functional FW health gate (pass/fail) for reseed rehearsal ([#35](https://github.com/by-openclaw/ansible-platform/issues/35)) ([7c8f844](https://github.com/by-openclaw/ansible-platform/commit/7c8f84420f0018ae4e220f798f6a73dc2b48aa4d))


### Bug Fixes

* **fw:** drop person-specific AdGuard rule — admin access is group-based ([78f6936](https://github.com/by-openclaw/ansible-platform/commit/78f6936903b79d8cbbec0ed0ce564be52acf47a7))
* **fw:** encode 2 drift rules ADR-compliant ([#47](https://github.com/by-openclaw/ansible-platform/issues/47)) ([454fa31](https://github.com/by-openclaw/ansible-platform/commit/454fa3153c16ab351d2ff2943f65df4fb64a3eb5))
* **fw:** encode 2 drift rules ADR-compliant (naming/0003) ([c382239](https://github.com/by-openclaw/ansible-platform/commit/c38223997ba2d1ce89293445883bd60dcb4a5237))
* **opnsense:** chrony serves NTP on :123 to internal nets (dual-stack) ([0e96cc6](https://github.com/by-openclaw/ansible-platform/commit/0e96cc66a374dfcc0b9ede41b8d84de01547de18))
* **opnsense:** correct mangled var ref in monit.yml secret lookup ([7e77770](https://github.com/by-openclaw/ansible-platform/commit/7e777700611c1e7b381333001be417665ec15f7d))
* **opnsense:** correct unbound forward schema + dual-stack loopback ([6691881](https://github.com/by-openclaw/ansible-platform/commit/6691881bee0a054f811c7e29df0bf7df4fa4ab08))
* **opnsense:** gate stale role tasks so an untagged prod run is idempotent ([#51](https://github.com/by-openclaw/ansible-platform/issues/51)) ([6099c12](https://github.com/by-openclaw/ansible-platform/commit/6099c12670fe94882ec1af17e7eac10a0881786f))
* **opnsense:** gate stale role tasks so an untagged prod run is idempotent ([#51](https://github.com/by-openclaw/ansible-platform/issues/51)) ([8e8316a](https://github.com/by-openclaw/ansible-platform/commit/8e8316a5126fa4bb27b052ce57020f03e1adc241))
* **opnsense:** install plugins sequentially, wait for each ([#41](https://github.com/by-openclaw/ansible-platform/issues/41)) ([caf70a7](https://github.com/by-openclaw/ansible-platform/commit/caf70a76198c6989000bea0a344b67fb01a01320))
* **opnsense:** poll firmware status until check settles ([#41](https://github.com/by-openclaw/ansible-platform/issues/41)) ([371530b](https://github.com/by-openclaw/ansible-platform/commit/371530bdcadd50d174c2de55e408b939918f131e))
* **opnsense:** unbound uses dnscrypt chain (plaintext), purge DoT ([f4eb432](https://github.com/by-openclaw/ansible-platform/commit/f4eb4328626c5134c5026b2b96a1798470610ac2))
* **opnsense:** use firmware/update for point releases, /upgrade for major ([#41](https://github.com/by-openclaw/ansible-platform/issues/41)) ([2877e75](https://github.com/by-openclaw/ansible-platform/commit/2877e7514cfba61469187048ae29346625e1e481))
* **opnsense:** wait for async firmware check to finish before reading status ([#41](https://github.com/by-openclaw/ansible-platform/issues/41)) ([0c6d388](https://github.com/by-openclaw/ansible-platform/commit/0c6d388aeeb9ff100c4950810378707e158cbf98))
* **opnsense:** wait for the NEW firmware version after reboot ([#41](https://github.com/by-openclaw/ansible-platform/issues/41)) ([5c732f4](https://github.com/by-openclaw/ansible-platform/commit/5c732f445e346b4893cc3662acef1edc392dcf5f))
* **scripts:** strip /prefix before WAN2 .222 suffix check ([#37](https://github.com/by-openclaw/ansible-platform/issues/37)) ([5743263](https://github.com/by-openclaw/ansible-platform/commit/574326388ff2d367f07abf05c09a4900d5e31e79))
* **scripts:** use final interface names in health gate ([#37](https://github.com/by-openclaw/ansible-platform/issues/37)) ([bbb123c](https://github.com/by-openclaw/ansible-platform/commit/bbb123c98ae9349772f126b0d917b06ffd6e260d))

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
