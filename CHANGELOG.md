# Changelog

All notable changes to ansible-platform are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [0.4.0](https://github.com/by-openclaw/ansible-platform/compare/v0.3.0...v0.4.0) (2026-06-07)


### Features

* **authentik:** Authentik SSO/IdP (Docker, community) — server+worker ([c4b6179](https://github.com/by-openclaw/ansible-platform/commit/c4b6179a6264bdb1cf6c2a995f33083009f32ffb))
* **authentik:** Authentik SSO/IdP (Docker) — server+worker, Postgres+Redis TLS ([74317dd](https://github.com/by-openclaw/ansible-platform/commit/74317dd847d5223dc60af1eeb109135afe9fece0)), closes [#87](https://github.com/by-openclaw/ansible-platform/issues/87)
* **authentik:** declarative per-service OIDC blueprints (SSO) — Vault first ([43b4984](https://github.com/by-openclaw/ansible-platform/commit/43b4984b9d118392c518b154158c77e0a02fea5e))
* **authentik:** identity blueprint (groups+users) + outbound SMTP via Resend ([f1ca236](https://github.com/by-openclaw/ansible-platform/commit/f1ca2362eaa8a4de506c8eec0faf208c8c6cde4d))
* **authentik:** platform-admins is a superuser group ([0841095](https://github.com/by-openclaw/ansible-platform/commit/0841095906b4cbb4f142bb1bcc3d2ba0589d05c8))
* **base:** shared baseline-packages role + wire cluster LXCs ([#60](https://github.com/by-openclaw/ansible-platform/issues/60)) ([5eba259](https://github.com/by-openclaw/ansible-platform/commit/5eba2596b7cdf038388ee59dd899311703377fac))
* **catalog:** clone Traefik dual-stack exposure for Defguard DMZ move ([122fe21](https://github.com/by-openclaw/ansible-platform/commit/122fe2130175ae4ea596729f07cb619b08ebdf8e))
* **catalog:** Defguard FW/DNS/NAT — alias, DMZ→SVC PASS, DNS, WG groups, WAN udp/51820 (staged) ([ae56ded](https://github.com/by-openclaw/ansible-platform/commit/ae56ded0dbcc0209766fa0615db6037d92b60c3c)), closes [#108](https://github.com/by-openclaw/ansible-platform/issues/108)
* **defguard:** point inventory at vm-defguard-01 (VM, by-systems+become) ([701251f](https://github.com/by-openclaw/ansible-platform/commit/701251feb3506705407bdef6243c536b2a465290))
* **defguard:** repoint Defguard to DMZ address 10.1.2.120 (SVC→DMZ move) ([bfb97f7](https://github.com/by-openclaw/ansible-platform/commit/bfb97f79bac6cf4202ffe80223fbb4c443e46a76))
* **defguard:** role + inventory for Defguard WireGuard VPN (Authentik OIDC, userspace WG) ([dd057e9](https://github.com/by-openclaw/ansible-platform/commit/dd057e98bf1bc92858b68fe018781d715becfba8)), closes [#106](https://github.com/by-openclaw/ansible-platform/issues/106)
* **docker:** mount host CA store into postgres + pgadmin containers (CA-by-default) ([933e430](https://github.com/by-openclaw/ansible-platform/commit/933e43025a02f6d34143d7be893adba40a4b49a1))
* **docker:** mount host CA store into postgres + pgadmin containers (CA-by-default) ([7bd9517](https://github.com/by-openclaw/ansible-platform/commit/7bd9517c9fb8c949a81f119462f50edef162dd99))
* **fw:** catalog the OOB admin-desk → Traefik access (de-drift) ([b25c42c](https://github.com/by-openclaw/ansible-platform/commit/b25c42cfe540717b5384fd0fb9cdae8cf3a14e08))
* **fw:** data-service port aliases (port_pgsql 5432, port_redis 6379) ([88676de](https://github.com/by-openclaw/ansible-platform/commit/88676de3679e1ab72daa6638ab607c9fa60e28a3)), closes [#69](https://github.com/by-openclaw/ansible-platform/issues/69)
* **fw:** data-service port aliases (port_pgsql, port_redis) ([ac56c10](https://github.com/by-openclaw/ansible-platform/commit/ac56c10c5b612a0c449d2751d0705dd6f4d66b67))
* **fw:** drift gate — fail loudly when live FW != catalog ([#35](https://github.com/by-openclaw/ansible-platform/issues/35)) ([9eb0e2c](https://github.com/by-openclaw/ansible-platform/commit/9eb0e2c9e4e4ee1b5806afada5c8c264796a2b2a))
* **fw:** public ingress — Telenet WAN2 (opt13) port-forward 80/443 → Traefik (dual-stack) ([27fcd3f](https://github.com/by-openclaw/ansible-platform/commit/27fcd3f43a4cdb0bf65ab62a88ac9d4fef5fa637)), closes [#60](https://github.com/by-openclaw/ansible-platform/issues/60)
* **fw:** public ingress — Telenet WAN2 port-forward 80/443 → Traefik (dual-stack) ([a8c4c00](https://github.com/by-openclaw/ansible-platform/commit/a8c4c00b6d6f9b1071054715b0dc43ac74230f3c))
* **fw:** publish Authentik via Traefik — aliases + DMZ→SVC rule + Unbound overrides ([87938fa](https://github.com/by-openclaw/ansible-platform/commit/87938fa4d8a6f4114e7d111ffe9ab8406a82308c)), closes [#89](https://github.com/by-openclaw/ansible-platform/issues/89)
* **fw:** publish Authentik via Traefik (DMZ→SVC rule + DNS) ([68bcf7f](https://github.com/by-openclaw/ansible-platform/commit/68bcf7fdfffa23c3efc0d09b50b52210d89855f5))
* **fw:** publish NetBox via Traefik — DMZ→SVC rule (seq 1056), aliases, Unbound overrides ([7036c14](https://github.com/by-openclaw/ansible-platform/commit/7036c1484f33351e361236b608c108a1bdc501b2))
* **fw:** publish NetBox via Traefik — DMZ→SVC rule seq 1056, aliases, Unbound overrides ([ef6cb8a](https://github.com/by-openclaw/ansible-platform/commit/ef6cb8a04fa7be56fa03fd7a58ab8742eddda94c)), closes [#96](https://github.com/by-openclaw/ansible-platform/issues/96)
* **fw:** publish Nextcloud — DMZ Traefik→SVC (seq 1060) + Unbound overrides ([60ebba2](https://github.com/by-openclaw/ansible-platform/commit/60ebba2cca5f980a3f3b2bcd30452d14471ed2b9))
* **fw:** publish Nextcloud — DMZ→SVC aliases + filter seq 1060 + Unbound overrides ([7409b64](https://github.com/by-openclaw/ansible-platform/commit/7409b64ba8d4e08f73a5f8afd098aa7411e951a8)), closes [#104](https://github.com/by-openclaw/ansible-platform/issues/104)
* **fw:** publish pgAdmin via Traefik — aliases + DMZ→SVC rule + Unbound overrides ([4f438ce](https://github.com/by-openclaw/ansible-platform/commit/4f438ce18bec7fd79e69b5c28d7208a1f2776b4f)), closes [#75](https://github.com/by-openclaw/ansible-platform/issues/75)
* **fw:** publish pgAdmin via Traefik (DMZ→SVC reverse-proxy rule + DNS) ([0468819](https://github.com/by-openclaw/ansible-platform/commit/04688195d76ca241179a9f8928fdb712ba269b15))
* **fw:** publish Vault via Traefik — aliases + DMZ→SVC rule + Unbound overrides ([0061abf](https://github.com/by-openclaw/ansible-platform/commit/0061abf1169478cfa6798ef3407b7a6cec45a97c)), closes [#92](https://github.com/by-openclaw/ansible-platform/issues/92)
* **fw:** publish Vault via Traefik (DMZ→SVC rule + DNS) ([d71b0f7](https://github.com/by-openclaw/ansible-platform/commit/d71b0f786465cfce62fc12b703f1b7d7263d7eb7))
* **fw:** publish Vaultwarden via Traefik — aliases + DMZ rule 1058 + Unbound overrides ([eb1a777](https://github.com/by-openclaw/ansible-platform/commit/eb1a777dd99e9418ab15473138c3ad7e935ef932)), closes [#100](https://github.com/by-openclaw/ansible-platform/issues/100)
* **fw:** publish Vaultwarden via Traefik — catalog aliases + DMZ rule 1058 + Unbound overrides ([12749db](https://github.com/by-openclaw/ansible-platform/commit/12749db9943fbcdc0cce635984252bf3a47f13fd))
* **ipv6:** dual-stack container networking + Postgres v6 publish ([3096d6a](https://github.com/by-openclaw/ansible-platform/commit/3096d6a6abc766e66a28b370086501a608d2d303))
* **netbox:** NetBox Docker role (Phase 6) — web+worker+housekeeping, Postgres+Redis TLS, Traefik internal ([4f21138](https://github.com/by-openclaw/ansible-platform/commit/4f21138d1123853b1061a3be8a556ef1711bc4e8))
* **netbox:** NetBox Docker role (Phase 6) — web+worker+housekeeping, Postgres+Redis TLS, Traefik internal ([e3b772c](https://github.com/by-openclaw/ansible-platform/commit/e3b772ce9450857fb0663f6d867911ee9a80b88a)), closes [#94](https://github.com/by-openclaw/ansible-platform/issues/94)
* **nextcloud:** role — Nextcloud (Docker) on lxc-nextcloud-01, Contabo S3 primary + drawio ([eb06f7d](https://github.com/by-openclaw/ansible-platform/commit/eb06f7d7ae0bcc4408d63aafdc709639eb213189)), closes [#102](https://github.com/by-openclaw/ansible-platform/issues/102)
* **nextcloud:** role — Nextcloud (Docker), Contabo S3 primary + drawio ([e05d69a](https://github.com/by-openclaw/ansible-platform/commit/e05d69a4a4d0d6016cc51bf82809446a45cb09f0))
* **opnsense:** add OOB break-glass admin provisioner (lib-opnsense MVC) ([b121d1c](https://github.com/by-openclaw/ansible-platform/commit/b121d1c3c024ad24d48abdd4c0be479b7cc9fc98))
* **pgadmin:** Authentik SSO + shared Postgres connection (idempotent) ([8c1dd6d](https://github.com/by-openclaw/ansible-platform/commit/8c1dd6d5eb45a1b6d5caa7e66c553f6bdf506726))
* **pgadmin:** Docker + pgAdmin + reusable traefik_route roles ([7dfc9de](https://github.com/by-openclaw/ansible-platform/commit/7dfc9de50a29589564d47cbc17019de806297a33))
* **pgadmin:** Docker + pgAdmin + reusable traefik_route roles ([22307c9](https://github.com/by-openclaw/ansible-platform/commit/22307c9d9b677fcc9acca6c69aa33c768345907b)), closes [#73](https://github.com/by-openclaw/ansible-platform/issues/73)
* **postgresql:** PostgreSQL 17 — data-persistent, HA-adoptable, app DBs (netbox/authentik) ([93b5911](https://github.com/by-openclaw/ansible-platform/commit/93b591113e7d5f354ce1a4f65481c32e53c23a19))
* **postgresql:** PostgreSQL 17 role (install/config/dbs/backup) + playbook ([#65](https://github.com/by-openclaw/ansible-platform/issues/65)) ([dd42490](https://github.com/by-openclaw/ansible-platform/commit/dd42490f9ecb6c5ad626c199d34f8c14115e6b81))
* **postgresql:** run PostgreSQL 17 as a Docker container (all-Docker pivot) ([c91806e](https://github.com/by-openclaw/ansible-platform/commit/c91806e150b7211967b2080481c1d3343f160215))
* **postgresql:** run PostgreSQL 17 as a Docker container (all-Docker pivot) ([9c940fd](https://github.com/by-openclaw/ansible-platform/commit/9c940fd57eeb7f0b885b7bd1af008740b1a8bacf)), closes [#77](https://github.com/by-openclaw/ansible-platform/issues/77)
* **redis:** Redis role — TLS (shared wildcard), auth, AOF-durable, HA-adoptable ([1da33b3](https://github.com/by-openclaw/ansible-platform/commit/1da33b3ca123695e0222827fa72675489681f34f)), closes [#71](https://github.com/by-openclaw/ansible-platform/issues/71)
* **redis:** Redis role — TLS, auth, AOF-durable, HA-adoptable (Phase 3) ([d09305b](https://github.com/by-openclaw/ansible-platform/commit/d09305ba81f08cd912b14f230533dad07ab2fec1))
* **redis:** run Redis 8 as a Docker container (all-Docker pivot) ([3f65060](https://github.com/by-openclaw/ansible-platform/commit/3f65060fb36d6ba4fd360aa8efdfd65340d3646d))
* **redis:** run Redis 8 as a Docker container (all-Docker pivot) ([b8d8735](https://github.com/by-openclaw/ansible-platform/commit/b8d873501220f6e08c01697be0e3d35b37e017b1)), closes [#81](https://github.com/by-openclaw/ansible-platform/issues/81)
* **tls_cert:** shared wildcard cert role + Postgres ssl=on ([c308ea9](https://github.com/by-openclaw/ansible-platform/commit/c308ea999f94e926de00aad1a455caa10c87d337))
* **tls_cert:** shared wildcard cert role + Postgres ssl=on ([163d908](https://github.com/by-openclaw/ansible-platform/commit/163d908bf24614e78028bd53c4a21376903edd7e)), closes [#67](https://github.com/by-openclaw/ansible-platform/issues/67)
* **tls:** transparent Postgres cert reload + scheduled certs-sync for renewals ([79cdb56](https://github.com/by-openclaw/ansible-platform/commit/79cdb56122300ece48dfb09dfa40cb053f618e5f))
* **tls:** transparent Postgres cert reload + scheduled certs-sync for renewals ([b1dfb7d](https://github.com/by-openclaw/ansible-platform/commit/b1dfb7d3c1f318a797fb9e77b9063d8d671040a3)), closes [#83](https://github.com/by-openclaw/ansible-platform/issues/83)
* **traefik:** admin_cidrs knob for OOB break-glass access (de-drift) ([b05a106](https://github.com/by-openclaw/ansible-platform/commit/b05a106863cc5f2c140e42bffa48713c1b6c1051))
* **traefik:** Traefik v3 ingress role (internal-complete) — ACME DNS-01 Cloudflare wildcard ([72cc013](https://github.com/by-openclaw/ansible-platform/commit/72cc013300cbe3293812e27bf8dda4af72d0acb4))
* **traefik:** Traefik v3 ingress role + inventory + playbook ([#60](https://github.com/by-openclaw/ansible-platform/issues/60)) ([67a8ec7](https://github.com/by-openclaw/ansible-platform/commit/67a8ec78000e1862c9f524ffdfc4ad92ce1abdca))
* **vault:** HashiCorp Vault (Docker) — raft, TLS wildcard, init+unseal ([afe11ab](https://github.com/by-openclaw/ansible-platform/commit/afe11ab678dce3c8379de026ab0d331be0205052))
* **vault:** HashiCorp Vault (Docker) — raft, TLS, init+unseal ([c163a48](https://github.com/by-openclaw/ansible-platform/commit/c163a485288805ae7d2ef6e67cd939c391dc79d3))
* **vault:** KV v2 store + Authentik OIDC SSO (Ansible-only) ([4216e69](https://github.com/by-openclaw/ansible-platform/commit/4216e69870f266458d813f2dc4018e5655ccb2e3))
* **vaultwarden:** roles/vaultwarden — Docker password manager (SVC, Postgres, Traefik) ([062c2e5](https://github.com/by-openclaw/ansible-platform/commit/062c2e59d3eb80d6facbf5a5d629f43d49e6be99))
* **vaultwarden:** roles/vaultwarden — Docker password manager on lxc-vaultwarden-01 ([230335d](https://github.com/by-openclaw/ansible-platform/commit/230335dd86ad357d863c30da06c2981ce09237fd)), closes [#98](https://github.com/by-openclaw/ansible-platform/issues/98)


### Bug Fixes

* **ansible:** move vault_password_file to [defaults] ([2e25589](https://github.com/by-openclaw/ansible-platform/commit/2e25589222ff5e8909758261227e00eee43b26d8))
* **authentik:** set grant_types on OIDC providers (fixes login) ([67ebb35](https://github.com/by-openclaw/ansible-platform/commit/67ebb3510b4086c8c0f1bdac4114b57d35ec8c75))
* **catalog:** Defguard WG ingress = pure alias-based port-forward (SVC, no Traefik) ([b8e75cd](https://github.com/by-openclaw/ansible-platform/commit/b8e75cd327e92a31d590e066577b256a2defe044))
* **catalog:** full dual-stack + alias-only WAN ingress (Traefik + Defguard) ([d981b33](https://github.com/by-openclaw/ansible-platform/commit/d981b33b274b81766a9787fd17903adad2f40948))
* **catalog:** rename internal DNS lxc-defguard-01 -&gt; vm-defguard-01 (VM migration) ([a244873](https://github.com/by-openclaw/ansible-platform/commit/a2448739607c2c22f5723923b1695286d4bbe387))
* **defguard:** gateway DEFGUARD_USERSPACE must be 'true'/'false' not '1'/'0' ([21efc42](https://github.com/by-openclaw/ansible-platform/commit/21efc426cd933a4d264b61ebd5c0dcadbf24ec64))
* **fw:** cluster host aliases + prune 20 stale Unbound overrides + real records ([3d5c006](https://github.com/by-openclaw/ansible-platform/commit/3d5c00602d70825d88cb2ca83082837fd895d9c3))
* **fw:** cluster host aliases + prune 20 stale Unbound overrides + real records ([c0918f1](https://github.com/by-openclaw/ansible-platform/commit/c0918f1f733bf2eb13f440d7c481a781def61f28)), closes [#62](https://github.com/by-openclaw/ansible-platform/issues/62)
* **opnsense:** never fabricate an OOB admin email ([cf913f9](https://github.com/by-openclaw/ansible-platform/commit/cf913f9cc9004e604bbb9d007380bcdf3e5d9a68))
* **pgadmin:** mount CA bundle at libpq default path for verify-full ([0daff85](https://github.com/by-openclaw/ansible-platform/commit/0daff85a3a2907539817fc487db29611d9a81756))
* **postgresql:** base installs sudo (become_user) + create DBs from template0 (cluster template1 is SQL_ASCII) ([511d3ec](https://github.com/by-openclaw/ansible-platform/commit/511d3ec272bef96227cee1e7abdc73bbf0a08fa5)), closes [#65](https://github.com/by-openclaw/ansible-platform/issues/65)
* **redis:** mount host CA store so in-container redis-cli verifies ([0e5809c](https://github.com/by-openclaw/ansible-platform/commit/0e5809c096f0433635c08dc4d72856125c11db71))
* **redis:** mount host CA store so in-container redis-cli verifies (not --insecure) ([b0bc0da](https://github.com/by-openclaw/ansible-platform/commit/b0bc0dad811e8860302f11a2884ff7dc6a0799fc))
* **traefik:** make admin_cidrs durable in routes; restore desk allowlist ([3207fbd](https://github.com/by-openclaw/ansible-platform/commit/3207fbd3030ae99a8722d57c67036aed7de7c053))

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
