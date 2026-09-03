<!--
Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
SPDX-License-Identifier: MIT
Repo: https://github.com/by-openclaw/ansible-platform
-->

# Security-Monitoring Stack — Mechanism Recommendation & Compliance Mapping

**Status:** Draft (ADR candidate — see §7)
**Date:** 2026-06-06
**Scope:** How to reproducibly manage the OPNsense-centred security-monitoring stack (CrowdSec central LAPI + agents, Suricata WAN IDS, AdGuard Home), and map every component to NIS2 / ISO 27001:2022 / GDPR.
**Drives roadmap:** #4 (CrowdSec full setup), #5 (AdGuard full setup), Suricata feed.
**Related:** `doc-platform-core/docs/adr/services/0006-firewall-services` (Suricata IDS + promotion gate), `doc-platform-core/docs/adr/services/0001-opnsense` (provisioning model), `doc-platform-core/docs/adr/security/0002-compliance-mapping` (compliance registry), `doc-platform-core/docs/adr/infra/0006-logging` (Loki), `doc-platform-core/docs/adr/security/0001-secret-storage`.

---

## 0. Verified current state (prod FW `10.6.239.196`, OPNsense 26.1.9)

- Suricata 8.0.5 installed; CrowdSec 1.7.8 + firewall-bouncer + `os-crowdsec` 1.0.12 running; CAPI + community blocklist + signals working.
- CrowdSec collections present: `freebsd, opnsense, opnsense-gui, sshd, whitelist-good-actors, pf`. **Missing:** `suricata, adguardhome, appsec`.
- LAPI listens `127.0.0.1:8080` only (not central); only localhost machine registered; acquisition = `opnsense.yaml` only (no suricata acquis); no AppSec configs.
- Catalog already carries an `opn_ids` block (`inventories/prod/group_vars/opnsense.yml:35`) — Suricata, currently `enabled: false` with `ref.adr: services/0006#§1-suricata-ids`.
- AdGuard Home is **already config-as-code**: full `roles/adguard/templates/AdGuardHome.yaml.j2` rendered deterministically, `querylog.enabled: true`, `interval: 2160h` (90 days).

---

## 1. The constraint that shapes everything

The platform mantra is "strict seed + ansible MVC exclusively, no manual config, no drift; issue→branch→PR". For the firewall that works because OPNsense exposes a clean MVC REST API wrapped by `lib-opnsense` managers and applied from a declarative catalog (`scripts/fw_apply_direct.py` + `inventories/<env>/group_vars/opnsense.yml`). The FW host is `connection: local` in the inventory (`inventories/prod/hosts.yml:24`) — Ansible never logs into it; it calls the API from the controller.

**The mismatch:** CrowdSec, Suricata, and AdGuard are configured by *files / cscli / service-REST*, almost none of which OPNsense MVC exposes. `os-crowdsec` MVC only exposes `crowdsec/general` (`lapi_enabled`, `lapi_listen_address`, `lapi_listen_port`, `enroll_key`) — confirmed against the `os-crowdsec` model and our seed `<plugins>` list (`infra-terraform-proxmox/.../seed/templates/baseline.xml:100`). Collections, acquisition YAML, parsers, and AppSec rules live under `/usr/local/etc/crowdsec/` and are driven by `cscli`. **Root SSH to the FW is blocked by design**; the only root path into the FW is break-glass via Proxmox `qm guest exec` (qemu-guest-agent), which is **not** an Ansible transport.

So the three hosts split into two management classes:

| Host class | Examples | Transport | Mechanism |
|---|---|---|---|
| **Normal Linux** | Proxmox nodes, AdGuard VM, future service VMs / Traefik | SSH (AdGuard via ProxyJump through FW per `hosts.yml`) | Ordinary Ansible roles: templated files + `cscli`/REST modules. CrowdSec agent + firewall-bouncer installed and configured here exactly like any package. |
| **OPNsense FW (special)** | `vm-opns-01` | MVC API (`connection: local`); break-glass `qm guest exec` | MVC for what it covers; a sanctioned **configd action** invoked over the API for the file-based remainder (see §2). |

---

## 2. Mechanism recommendation (the decision)

**Recommended: a hybrid, two-track model — dedicated Ansible roles for the normal-Linux hosts, and for the OPNsense box a thin "CrowdSec/Suricata bootstrap" driven through the OPNsense API surface (configd action) so it stays inside the API door rather than the break-glass door, with the *declarative intent* (which collections, which acquis, LAPI listen/TLS, AppSec on/off) living in the existing catalog under new `opn_crowdsec` / extended `opn_ids` keys.**

One paragraph, concretely: For Proxmox + service VMs, write a `crowdsec_agent` role (install repo + agent + firewall-bouncer, template `acquis.d/*.yaml`, manage collections via `cscli collections install/remove` made idempotent with a `cscli collections list -o json` pre-check, register to the central LAPI with `cscli lapi register`/watcher creds, drop the bouncer API key from the secret store). For AdGuard, **keep the existing `roles/adguard` config-as-code path** — it already renders the full `AdGuardHome.yaml` and is the model the rest should follow; only add the CrowdSec acquisition of AdGuard's query log on whatever host scrapes it. For the OPNsense FW, do **not** try to force file edits through Ansible-over-SSH (no root) and do **not** make `qm guest exec` the routine path (it is break-glass, not idempotent transport). Instead:

1. **Use `os-crowdsec` MVC for what it exposes** — `crowdsec/general` (LAPI enable, listen address/port, enroll key) via a small `lib-opnsense` `CrowdSecGeneralManager` (option (c) below), so central-LAPI enablement and enrollment are catalog-driven and reviewable like every other FW setting.
2. **Bake the collection set + acquisition + Suricata eve transform into the SEED** as a first-boot configd/rc step (option (b)), because these are slow-changing, OS-level facts that belong with the image — same ownership logic the seed already uses for `<plugins>` and that `recreate-and-seed-prod.py::apply_security_baseline()` already uses for NetFlow/Unbound-stats post-reseed. The seed's existing post-reseed Python (`recreate-and-seed-prod.py`) is the natural home: extend `apply_security_baseline()` with a `cscli collections install suricata adguardhome appsec` step executed once via the documented break-glass `qm guest exec` **at build/reseed time only**, then captured in the seed so a fresh image already has them.
3. **For day-2 drift-free changes to those file-based bits**, expose them through a **sanctioned OPNsense `configd` action** (a small custom actions file shipped in the seed, e.g. `actions_crowdsec.conf` calling a script that runs the desired `cscli`), callable over the MVC API (`/api/core/...` configd bridge). This keeps "change a collection" inside the API door: issue→PR edits the catalog `opn_crowdsec.collections` list → Ansible calls the configd action with the desired set → the FW reconciles → verify via `cscli collections list -o json` read back through the same action. Idempotency is the script's job (install-if-absent / remove-if-extra against the declared set).

### Why not the alternatives (explicitly)
- **(a) pure Ansible role reaching the FW over SSH** — impossible for the file-based parts: root SSH blocked; `by-rune` is non-root and `/usr/local/etc/crowdsec` is root-owned. Rejected for the FW; *adopted* for Proxmox/VMs where SSH is normal.
- **(b) seed-only** — correct for the slow, OS-level baseline (collections, acquis, eve transform) and for surviving upgrades, but a seed reseed is too heavy for a routine "add a collection" change. Adopted **for the baseline**, paired with (3) for day-2.
- **(c) extend `lib-opnsense` with a manager** — adopted but *bounded*: a `CrowdSecGeneralManager` for the real MVC surface (`crowdsec/general`) and, optionally, a thin manager that calls the §2.3 configd action. Do **not** invent MVC endpoints that `os-crowdsec` does not have.
- **(d) AdGuard via its YAML under config management** — already done and is the gold standard; keep it.

### Change flow (issue→PR→apply→verify), file-by-file
- **FW LAPI/enrollment:** edit `opn_crowdsec.lapi` in `inventories/prod/group_vars/opnsense.yml` → PR → `fw_apply_direct.py` (new `CrowdSecGeneralManager.ensure`) → verify `cscli lapi status` via configd read-back + `crowdsec/general` GET.
- **FW collections / acquis / AppSec:** edit `opn_crowdsec.collections` / `opn_ids` → PR → Ansible calls configd action `crowdsec reconcile` → verify `cscli collections list -o json` + `cscli metrics`.
- **Suricata IDS:** flip `opn_ids.enabled` / interfaces / rulesets in catalog (already structured) → PR → MVC `intrusion-detection` settings + reconfigure (new `ids.yml` task; the role's `services.yml` already reconfigures via `/api/{plugin}/service/reconfigure`).
- **Agents (Proxmox/VMs):** edit host/group vars `crowdsec_collections` → PR → `crowdsec_agent` role → verify `systemctl is-active crowdsec` + `cscli metrics` + agent shows in central LAPI `cscli machines list`.
- **AdGuard:** edit `roles/adguard/defaults` (filters/clients) → PR → `roles/adguard/tasks/config.yml` re-renders `AdGuardHome.yaml` + restart handler → verify via AdGuard API `/control/status`.

**Every change is reproducible (catalog/role is source of truth), idempotent (ensure / install-if-absent / templated file), reviewable (PR with the mandatory template), and survives upgrades (baseline in seed, day-2 via configd not hand edits).** This is an ADR candidate (§7) because it deliberately extends the "MVC + catalog + no drift" model with a sanctioned configd lane for the file-based stack — that is an architectural decision, not just a config.

---

## 3. Central-LAPI design

Today LAPI = `127.0.0.1:8080`, localhost-only. To make `vm-opns-01` the central LAPI for all agents:

- **Listen address:** bind LAPI to the OOB/management interface IP (and/or a dedicated mgmt VLAN address) — **not** `0.0.0.0` and **not** WAN. Set via `crowdsec/general.lapi_listen_address` (MVC) → catalog `opn_crowdsec.lapi.listen_address`. Keep `127.0.0.1` reachable for the local agent.
- **TLS:** enable LAPI TLS (CrowdSec supports server cert + optional client-cert/agent auth). Issue the LAPI server cert from the platform ACME/internal CA (we already run `lego` for AdGuard; reuse). Agents pin the CA. This is config under `/usr/local/etc/crowdsec/config.yaml` `api.server.tls` → owned by the seed baseline (§2.2) + day-2 via configd.
- **Machine registration / enrollment:**
  - Each agent registers as a *machine* (watcher) to the central LAPI: `cscli lapi register -u https://<fw-mgmt-ip>:8080 --machine <hostname>` then validated centrally with `cscli machines validate <hostname>` (or auto-validate via shared registration token). Run from the `crowdsec_agent` role; the validate step runs against the FW configd action.
  - Console enrollment (CAPI/console) uses the `enroll_key` field already in `crowdsec/general` MVC — **user-supplied secret** (§7 flags).
- **Bouncer key distribution:** the firewall-bouncer on the FW already has its local key. For any *remote* bouncer (e.g. Traefik AppSec bouncer, roadmap #6), generate the key centrally with `cscli bouncers add <name> -o raw`, **store it in the secret store** `~/.openclaw/workspace/infra/secrets/crowdsec-bouncer-<name>.json` (never echo to terminal), and have the consuming role read it via lookup — exactly the pattern `roles/adguard/defaults/main.yml` uses for `adguard_secret` / `adguard_cf_secret`.
- **Implied firewall rules (lib-first, into the catalog):** add FwFilter rules in `opn_filter_rules` allowing `agents → FW:8080/tcp` **only** from the internal management/server sources (an alias `grp_net4_crowdsec_agents`), default-deny otherwise; LAPI never exposed to WAN or guest/IoT VLANs. These go through the normal `FwFilterManager`/`FwAliasManager` path — no new mechanism.
- **Anti-self-lockout / allowlist:** add the FW's own mgmt addresses, the agent source ranges, and the controller (Rune) to CrowdSec's `whitelists` (parser whitelist) so the bouncer can never block the management plane. The `whitelist-good-actors` collection is already present; add an explicit `crowdsecurity/whitelists` entry seeded with the internal CIDRs (catalog `opn_crowdsec.allowlist`). This is roadmap step 4.x and must land **before** central LAPI goes live.

---

## 4. Suricata → CrowdSec (the hard part)

Suricata on OPNsense writes `eve.json`. CrowdSec's canonical integration is the **`crowdsecurity/suricata` collection**, which ships the parser that understands Suricata's `eve.json` alert events; you point CrowdSec acquisition at the eve log and install the collection. Recommended, upgrade-surviving approach:

1. **Suricata config (MVC + seed):** enable Suricata in IDS/alert mode on WAN via the catalog `opn_ids` block (already structured: `mode: alert`, `interfaces: [wan]`, `rulesets`, `home_net_alias`). Apply via a new `roles/opnsense/tasks/ids.yml` using the `intrusion-detection` API (settings/set + service/reconfigure) — consistent with services/0006 which references exactly `roles/opnsense/tasks/ids.yml`. Ensure Suricata's **EVE JSON output** is enabled and writes a stable path (OPNsense default `/var/log/suricata/eve.json`). EVE log-type selection (alert at minimum; optionally http/dns/tls for richer parsing) is set in Suricata's output config — part of the seed baseline so it survives plugin upgrades.
2. **Install the parser collection:** `cscli collections install crowdsecurity/suricata` — via the §2 mechanism (baseline seed + day-2 configd). This is what brings the eve.json → CrowdSec event transform; **do not hand-write a custom parser** — the maintained collection is the supported path and tracks Suricata schema changes across upgrades.
3. **Acquisition:** add `/usr/local/etc/crowdsec/acquis.d/suricata.yaml`:
   ```yaml
   filenames:
     - /var/log/suricata/eve.json
   labels:
     type: suricata-evt
   ```
   The `type: suricata-evt` label is what the `crowdsecurity/suricata` parser keys on. This file is owned by the seed baseline (so it survives) and reconciled day-2 by the configd action. Restart/reload CrowdSec after acquis changes (`cscli` reload via the action).
4. **Decision split (unchanged from services/0006):** Suricata = sensor (alert-only at first, IPS promotion gated); CrowdSec = decision + bouncer. Suricata alerts become CrowdSec signals → scenarios → firewall-bouncer decisions, **and** in parallel still go to Loki (`service=ids`) per services/0006 §logging.
5. **Upgrade survival:** because (a) the acquis file + EVE output config live in the seed, (b) collections are reinstalled idempotently from the declared set, and (c) we rely on the maintained `crowdsecurity/suricata` collection rather than a bespoke parser, an OPNsense/Suricata/CrowdSec upgrade re-converges without hand-editing.

---

## 5. Compliance matrix

Per `security/0002-compliance-mapping`, control IDs belong in a `CISO mapping`-style table that feeds ciso-assistant; this is that input table for the security-monitoring stack.

| Component | NIS2 (Art. 21(2)) | ISO/IEC 27001:2022 Annex A | GDPR | Notes / risk |
|---|---|---|---|---|
| **CrowdSec engine (LAPI + scenarios + decisions)** | (b) incident handling; (e) network & info-systems security; (g) cyber hygiene | A.8.16 monitoring activities; A.8.20 networks security; A.5.30 ICT readiness for continuity | Art. 32 security of processing | Decision/quarantine layer; allowlist must protect mgmt plane (§3). |
| **CrowdSec community blocklist (CAPI)** | (d) supply-chain / shared threat data; (e) | A.5.7 threat intelligence; A.8.7 protection against malware | Art. 32; **Art. 44+ transfer caveat** | **RISK:** signal-sharing to CAPI = outbound data transfer (attacker IPs + scenario, *not* victim PII; still a data flow leaving the org). Document what is shared, that it is opt-out-able, and DPA/transfer basis. Internal source IPs in allowlist are not shared. |
| **Firewall bouncer (everywhere)** | (b) incident handling (active mitigation); (e) | A.8.20 networks security; A.8.16 monitoring (enforcement) | Art. 32 | Enforcement point; anti-lockout allowlist mandatory before central LAPI go-live. |
| **Suricata WAN IDS (sensor)** | (b) incident handling; (e); (g) | A.5.7 threat intelligence (rulesets); A.8.16 monitoring; A.8.20 networks security (edge IDS) | Art. 32 | Alerts → Loki + CrowdSec. eve.json may contain payload/IP metadata → treat log as containing personal data (retention below). Matches services/0006 mapping. |
| **AdGuard Home filtering (DNS chain front)** | (e); (g) cyber hygiene | A.8.23 web filtering; A.8.7 malware (phishing/malware blocklists); A.5.7 threat intelligence (filter feeds) | Art. 32 | Phishing/malware/tracker blocklists already configured. |
| **AdGuard query log** | (b) (forensics) | A.8.15 logging | **Art. 30 records; Art. 32; Art. 5(1)(c)+(e) minimisation & storage limitation** | **RISK:** DNS query log = **personal data** (who looked up what). Current `interval: 2160h` (90d). Needs a documented retention/minimisation policy; consider `anonymize_client_ip` for zones where attribution isn't required. |
| **Central log / SIEM aspect (Loki; future Wazuh)** | (b) incident handling; (g) | A.8.15 logging; A.8.16 monitoring activities; A.5.30 ICT readiness; **A.8.6 capacity** (log volume sizing) | Art. 33 breach-notification readiness; Art. 30 | Loki per `infra/0006-logging`. Capacity (A.8.6) = log storage sizing for IDS/DNS volume. Breach-notification readiness (Art. 33) depends on this pipeline existing. |
| **AppSec / WAF (CrowdSec AppSec; Traefik feed, #6)** | (b); (e) | A.8.20 networks security; A.8.26 application security requirements; A.8.16 monitoring | Art. 32 | `appsec` collection missing today; lands with Traefik (#6). |

**Cross-cutting GDPR notes:** (1) Both CrowdSec CAPI sharing and AdGuard query logging must appear in the Art. 30 **records of processing**. (2) Define a **retention schedule** (eve.json, AdGuard query log, CrowdSec decisions DB) — storage limitation. (3) The whole stack is the technical backbone of **Art. 33 breach-notification readiness** — claimable only once central logging is live.

---

## 6. Sequenced action plan

Seq numbers map to roadmap #4 (CrowdSec), #5 (AdGuard), plus the Suricata feed and compliance artifacts. `[secret]` = needs a user-supplied secret/external resource. `[policy]` = documented policy, not a technical control. `[tech]` = technical control.

### 4 — CrowdSec full setup (FW central LAPI + agents)
- **4.1 [tech]** Add `lib-opnsense` `CrowdSecGeneralManager` (wraps `crowdsec/general`: lapi_enabled, listen_address, listen_port, enroll_key) + unit tests + api-coverage update. *(lib PR)*
- **4.2 [tech]** Add catalog `opn_crowdsec` block to `inventories/prod/group_vars/opnsense.yml`: `lapi.{listen_address, port, tls}`, `collections: [freebsd, opnsense, opnsense-gui, sshd, suricata, whitelist-good-actors, pf, adguardhome, appsec]`, `allowlist: [<mgmt/agent CIDRs>]`, `ref.adr`.
- **4.3 [tech]** Anti-self-lockout **first**: add internal allowlist (parser whitelist) + FwFilter rules `agents→FW:LAPI` (alias `grp_net4_crowdsec_agents`, default-deny) via existing `FwAliasManager`/`FwFilterManager`. Verify mgmt plane cannot be bounced.
- **4.4 [tech]** Ship the **configd action** (`actions_crowdsec.conf` + reconcile script) in the seed (`infra-terraform-proxmox/modules/vm-opnsense/seed`) so the file-based bits are reachable through the API door.
- **4.5 [tech]** Install missing FW collections (`suricata, adguardhome, appsec`) via baseline seed step (extend `recreate-and-seed-prod.py::apply_security_baseline()`), reconcile day-2 via 4.4. Verify `cscli collections list -o json`.
- **4.6 [tech]** Flip LAPI to central (bind mgmt IP + TLS) via 4.1/4.2; enroll console with **`enroll_key` [secret]** (user-supplied CrowdSec console key).
- **4.7 [tech]** `crowdsec_agent` Ansible role for Proxmox nodes (collections: `linux, sshd, whitelist-good-actors, proxmox`) + firewall-bouncer; register to central LAPI; `cscli machines validate` via 4.4. Verify in `cscli machines list`.
- **4.8 [tech]** Extend `crowdsec_agent` to service VMs (incl. AdGuard VM: agent reads AdGuard query log for the `adguardhome` collection). **[secret]** remote bouncer keys → secret store.

### 5 — AdGuard full setup (config-as-code, already strong)
- **5.1 [tech]** Confirm the user's filter set (AdGuard DNS filter, StevenBlack, Dan Pollock, Peter Lowe, Hagezi Windows/Office, phishing + malicious URL blocklists) is fully expressed in `roles/adguard/defaults/main.yml` `adguard_filters` and re-render. Verify `/control/status`.
- **5.2 [tech]** Wire CrowdSec `adguardhome` acquisition to AdGuard's query log on the host running its agent (4.8); verify parser sees events (`cscli metrics`).
- **5.3 [policy] [tech]** AdGuard query-log retention/minimisation: set a justified `querylog.interval`, evaluate `anonymize_client_ip` per zone; record decision.

### S — Suricata feed
- **S.1 [tech]** `roles/opnsense/tasks/ids.yml` driving `opn_ids` via `intrusion-detection` API; enable EVE JSON output to `/var/log/suricata/eve.json` (alert min). Keep `mode: alert` (services/0006 promotion gate).
- **S.2 [tech]** `cscli collections install crowdsecurity/suricata` (via 4.4/4.5) + acquis.d/suricata.yaml (`type: suricata-evt`) in seed baseline. Verify CrowdSec parses eve events.
- **S.3 [tech]** Confirm dual sink: Suricata alerts → Loki (`service=ids`) **and** → CrowdSec signals.

### C — Compliance artifacts
- **C.1 [policy]** Records of processing (Art. 30) entries for CrowdSec CAPI sharing + AdGuard query log.
- **C.2 [policy]** Retention schedule: eve.json, AdGuard query log, CrowdSec decisions DB (GDPR storage limitation; ISO A.8.15).
- **C.3 [policy]** Document the CAPI signal-sharing transfer basis + what data leaves (attacker IPs/scenarios only; internal allowlist excluded) — GDPR transfer caveat.
- **C.4 [tech] [policy]** Feed this stack's `CISO mapping` (the §5 table) into ciso-assistant per `security/0002`; mark A.8.6 (log capacity) and Art. 33 readiness as dependent on Loki being live (`infra/0006-logging`).
- **C.5 [policy]** Promote this report to a scoped ADR (likely `services/0008` or `security/0006`) with a `CISO mapping` section — it records the sanctioned-configd-lane decision (§2).

### External / user inputs required (flagged)
- CrowdSec **console enroll key** (`enroll_key`) — user-supplied **[secret]** (4.6).
- Internal CA / ACME issuance for **LAPI TLS server cert** (reuse `lego`) (3 / 4.6).
- Remote **bouncer API keys** for Traefik AppSec (roadmap #6) → secret store (4.8).
- Confirmation of mgmt/agent **source CIDRs** for the allowlist + FwFilter rule (4.3).

---

## 7. ADR candidacy

This recommendation introduces a *new architectural lane* — a sanctioned OPNsense **configd action** for the file-based CrowdSec/Suricata stack, alongside the existing MVC-catalog model — plus seed-owned security baselines. That is a decision, not a config, so it should be promoted to a scoped ADR in `doc-platform-core` (matching the `# {scope}/NNNN — Title` + Context/Decision/Consequences/**CISO mapping** format) and cross-linked from `services/0006`. Until then, this file is the working reference for roadmap #4/#5 and the Suricata feed.
