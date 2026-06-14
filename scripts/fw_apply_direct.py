#!/usr/bin/env python3
# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/ansible-platform
"""Pass 1 — apply OPNsense firewall catalog via direct lib-opnsense MVC API.

Reads:
    inventories/<env>/group_vars/opnsense.yml      — full catalog (aliases + rules + NAT)
    secrets/net-opnsense-<env>-poc.json            — API credentials

Applies, in order:
    1. Aliases    (FwAliasManager.ensure)
    2. Filter rules (FwFilterManager.ensure)
    3. Source NAT (FwSourceNatManager.ensure)
    4. D-NAT       (FwDnatManager.ensure)

Each ensure() call carries the entry's `ref` block for end-of-run traceability.

This script is the Pass 1 validation tool (services/0001 phase 2 sanity check, run
before the Pass 2 Ansible playbook). Same YAML feeds both passes.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseError
from opnsense.managers.auth.group import AuthGroupManager
from opnsense.managers.auth.user import AuthUserManager
from opnsense.managers.firewall.alias import FwAliasManager
from opnsense.managers.firewall.dnat import FwDnatManager
from opnsense.managers.firewall.filter import FwFilterManager
from opnsense.managers.firewall.source_nat import FwSourceNatManager
from opnsense.managers.dns.ub_host_override import UbHostOverrideManager
from opnsense.managers.dns.ub_forward import UbForwardManager
from opnsense.managers.dhcp.kea4_subnet import Kea4SubnetManager
from opnsense.managers.dhcp.kea6_subnet import Kea6SubnetManager
from opnsense.managers.services.dnsmasq_boot import DnsmasqBootManager
from opnsense.managers.services.dnsmasq_domain import DnsmasqDomainManager
from opnsense.managers.services.dnsmasq_host import DnsmasqHostManager
from opnsense.managers.services.dnsmasq_option import DnsmasqOptionManager
from opnsense.managers.services.dnsmasq_range import DnsmasqRangeManager
from opnsense.managers.services.dnsmasq_service import DnsmasqServiceManager
from opnsense.managers.services.dnsmasq_settings import DnsmasqSettingsManager
from opnsense.managers.services.dnsmasq_tag import DnsmasqTagManager
from opnsense.managers.services.radvd_entry import RadvdEntryManager
from opnsense.managers.services.radvd_service import RadvdServiceManager

DEFAULT_ENV = "test"
WORKSPACE_SECRETS = Path("/home/by-systems/.openclaw/workspace/infra/secrets")
REPO_ROOT = Path(__file__).resolve().parents[1]

# Section groups selectable via --only. Each maps to one catalog concern so a
# roadmap step can apply just its slice without touching the others:
#   fw      -> opn_aliases, opn_filter_rules, opn_snat_rules, opn_dnat_rules
#   dns     -> opn_unbound (host overrides + forwarders)
#   kea     -> opn_kea_dhcp4 / opn_kea_dhcp6
#   dnsmasq -> opn_dnsmasq
#   radvd   -> opn_radvd
#   auth    -> opn_auth (local WebGUI admin users + group hygiene)
SECTION_GROUPS = {"fw", "dns", "kea", "dnsmasq", "radvd", "auth"}

log = logging.getLogger("fw_apply_direct")


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _as_bool(v: Any) -> bool:
    """Coerce JSON-ish truthy values to bool. `"false"` must be False, not True."""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def load_credentials(env: str, secret_file: str | None = None) -> dict[str, Any]:
    """Read API credentials from the per-env secret file (or an explicit override).

    Default path: secrets/net-opnsense-<env>-poc.json
    Override:     --secret-file <path>
    Required fields: host, port, key, secret, verify_ssl
    """
    secret_path = Path(secret_file) if secret_file else WORKSPACE_SECRETS / f"net-opnsense-{env}-poc.json"
    if not secret_path.exists():
        raise SystemExit(f"Secret file missing: {secret_path}")
    if oct(secret_path.stat().st_mode)[-3:] not in {"600", "400"}:
        log.warning("Secret file %s mode is not 0600/0400 — please tighten", secret_path)
    data = json.loads(secret_path.read_text())
    fields = data.get("fields", {})
    for key in ("host", "key", "secret"):
        if not fields.get(key):
            raise SystemExit(f"Secret file missing field 'fields.{key}'")
    return {
        "host": fields["host"],
        "port": int(fields.get("port") or 443),
        "key": fields["key"],
        "secret": fields["secret"],
        "verify_ssl": _as_bool(fields.get("verify_ssl", False)),
    }


def load_catalog(env: str) -> dict[str, Any]:
    catalog_path = REPO_ROOT / "inventories" / env / "group_vars" / "opnsense.yml"
    if not catalog_path.exists():
        raise SystemExit(f"Catalog file missing: {catalog_path}")
    return yaml.safe_load(catalog_path.read_text())


def strip_ref(entry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Separate `ref` metadata from API payload (lib-opnsense managers don't accept it)."""
    payload = {k: v for k, v in entry.items() if k not in ("ref", "state")}
    state = entry.get("state", "present")
    ref = entry.get("ref", {})
    return payload, {"state": state, "ref": ref}


def resolve_user_password(entry: dict[str, Any]) -> dict[str, Any]:
    """Inject a WebGUI password for an opn_auth user that declares `password_ref`.

    OPNsense requires a non-empty password on auth/user/add even for accounts that
    authenticate via the Authentik LDAP authserver. We never put a secret in the
    committed catalog, so the user declares `password_ref` = the basename of a
    secret file under the workspace secret folder; the password lives there only.

    Self-bootstrapping + idempotent: if the secret file is absent, generate a
    strong random password (the account authenticates via LDAP, so this local
    password is effectively never used for login) and write it 0600; reuse the
    same stored value on every run so ensure() converges to noop (bcrypt compare).
    The secret is read silently and never printed to the terminal.
    """
    ref = entry.get("password_ref")
    if not ref:
        return entry
    out = {k: v for k, v in entry.items() if k != "password_ref"}
    sf = WORKSPACE_SECRETS / f"{ref}.json"
    if sf.exists():
        fields = json.loads(sf.read_text()).get("fields", {})
        pw = fields.get("webgui_password")
        if not pw:
            raise SystemExit(f"Secret file {sf} missing field 'fields.webgui_password'")
    else:
        import secrets as _secrets
        import string as _string
        alphabet = _string.ascii_letters + _string.digits
        pw = "".join(_secrets.choice(alphabet) for _ in range(32))
        sf.write_text(json.dumps({"fields": {
            "webgui_password": pw,
            "note": ("Random local WebGUI password for the LDAP-shadow admin. Login is "
                     "via the Authentik LDAP authserver; this only satisfies OPNsense's "
                     "required-password field and is not used for interactive login."),
        }}, indent=2) + "\n")
        sf.chmod(0o600)
        log.info("[AUTH_USR] bootstrapped random local password -> %s (0600)", sf)
    out["password"] = pw
    return out


def normalize_alias(payload: dict[str, Any]) -> dict[str, Any]:
    """OPNsense alias `content` must be a string. Networkgroup/host aliases with
    multiple members come from YAML as a list — join with newlines."""
    out = dict(payload)
    if isinstance(out.get("content"), list):
        out["content"] = "\n".join(str(x) for x in out["content"])
    return out


def normalize_rule(payload: dict[str, Any], iface_map: dict[str, str]) -> dict[str, Any]:
    """Apply catalog→FW translations:
       1. interface friendly-name → OPNsense slot id (mgmt → opt2 etc.)
       2. protocol "any" with destination_port → "tcp/udp" (OPNsense validator)
       3. uppercase protocol names — OPNsense stores tcp/udp/icmp as TCP/UDP/ICMP;
          lib-opnsense search compares case-sensitively → mismatch creates duplicates
    """
    out = dict(payload)
    if "interface" in out and out["interface"] in iface_map:
        out["interface"] = iface_map[out["interface"]]
    if out.get("destination_port") and out.get("protocol") in ("any", None):
        out["protocol"] = "tcp/udp"
    # Normalize protocol case to match what OPNsense returns on search
    proto = out.get("protocol")
    if proto and proto.lower() in ("tcp", "udp", "icmp", "icmpv6", "esp", "ah", "tcp/udp"):
        out["protocol"] = proto.upper() if proto.lower() != "tcp/udp" else "TCP/UDP"
    return out


def normalize_snat(payload: dict[str, Any], iface_map: dict[str, str]) -> dict[str, Any]:
    out = dict(payload)
    if "interface" in out and out["interface"] in iface_map:
        out["interface"] = iface_map[out["interface"]]
    return out


def normalize_kea_subnet(payload: dict[str, Any], iface_map: dict[str, str]) -> dict[str, Any]:
    """Kea6 subnet `interface` is a friendly name in the catalog (mgmt/dmz/...)
    — translate to OPNsense slot (opt2/opt3/...). Kea4 has no per-subnet iface."""
    out = dict(payload)
    if "interface" in out and out["interface"] in iface_map:
        out["interface"] = iface_map[out["interface"]]
    return out


def normalize_radvd(payload: dict[str, Any], iface_map: dict[str, str]) -> dict[str, Any]:
    """radvd entry `interface` + `Base6Interface` are friendly names in the catalog
    (mgmt/dmz/...) — translate to OPNsense slot ids (opt2/opt3/...).

    OPNsense rejects `Base6Interface` equal to `interface` ("Constructor cannot be
    the same as interface"). For stateless mode with a static IPv6 prefix on the
    LAN/OPT, `Base6Interface` should be empty; only set it when tracking a prefix
    delegated from a different upstream interface.
    """
    out = dict(payload)
    if "interface" in out and out["interface"] in iface_map:
        out["interface"] = iface_map[out["interface"]]
    if out.get("Base6Interface"):
        if out["Base6Interface"] in iface_map:
            out["Base6Interface"] = iface_map[out["Base6Interface"]]
    return out


async def apply_kea_general(
    client: OpnsenseClient,
    endpoint: str,
    general: dict[str, Any],
    iface_map: dict[str, str],
    label: str,
    check_mode: bool,
    results: list[dict[str, Any]],
) -> None:
    """Enable Kea (v4 or v6) and bind it to interfaces.

    OPNsense expects `general.interfaces` as a comma-separated string of slot ids.
    We translate from catalog friendly names (mgmt/dmz/...) via iface_map.
    """
    ifaces_friendly = general.get("interfaces", []) or []
    ifaces_slots = [iface_map.get(f, f) for f in ifaces_friendly]
    payload_general = {k: v for k, v in general.items() if k != "interfaces"}
    payload_general["interfaces"] = ",".join(ifaces_slots)

    key = endpoint.split("/")[-1]  # dhcpv4 or dhcpv6
    body = {key: {"general": payload_general}}
    ident = f"{label} general (enabled={payload_general.get('enabled')}, iface={payload_general['interfaces']})"
    start = time.monotonic()
    try:
        if check_mode:
            log.info("[%s] DRY-RUN would POST kea/%s/set body=%s", label, key, body)
            outcome, action = "ok", "noop"
        else:
            await client.post(f"kea/{key}/set", body)
            outcome, action = "ok", "configured"
        dur_ms = int((time.monotonic() - start) * 1000)
        log.info("[%s] %-8s %s (%d ms)", label, "OK", ident, dur_ms)
    except Exception as exc:  # noqa: BLE001
        dur_ms = int((time.monotonic() - start) * 1000)
        outcome, action = "error", None
        log.exception("[%s] FAIL %s: %s (%d ms)", label, ident, exc, dur_ms)
    results.append({
        "section": label, "name": ident, "outcome": outcome, "action": action,
        "uuid": None, "changed": None, "duration_ms": dur_ms,
        "adr_ref": "infra/0004", "lib_manager": "raw_post", "ansible_module": None,
    })


async def reconfigure_kea(client: OpnsenseClient, check_mode: bool, results: list[dict[str, Any]]) -> None:
    start = time.monotonic()
    try:
        if check_mode:
            log.info("[KEA] DRY-RUN would POST kea/service/reconfigure")
            outcome, action = "ok", "noop"
        else:
            await client.post("kea/service/reconfigure", {})
            outcome, action = "ok", "reconfigured"
        dur_ms = int((time.monotonic() - start) * 1000)
        log.info("[KEA] %-8s reconfigure (%d ms)", "OK", dur_ms)
    except Exception as exc:  # noqa: BLE001
        dur_ms = int((time.monotonic() - start) * 1000)
        outcome, action = "error", None
        log.exception("[KEA] FAIL reconfigure: %s (%d ms)", exc, dur_ms)
    results.append({
        "section": "KEA", "name": "reconfigure", "outcome": outcome, "action": action,
        "uuid": None, "changed": None, "duration_ms": dur_ms,
        "adr_ref": "infra/0004", "lib_manager": "raw_post", "ansible_module": None,
    })


async def apply_section(
    manager_cls,
    client: OpnsenseClient,
    entries: list[dict[str, Any]],
    label: str,
    check_mode: bool,
    results: list[dict[str, Any]],
    iface_map: dict[str, str] | None = None,
) -> None:
    if not entries:
        log.info("[%s] no entries — skipping", label)
        return
    mgr = manager_cls(client)
    log.info("[%s] applying %d entries", label, len(entries))
    for entry in entries:
        payload, meta = strip_ref(entry)
        # Normalize payloads that reference interfaces by friendly name + protocol/port quirks
        if label == "ALIAS":
            payload = normalize_alias(payload)
        elif iface_map is not None:
            if label == "RULE":
                payload = normalize_rule(payload, iface_map)
            elif label == "SNAT":
                payload = normalize_snat(payload, iface_map)
            elif label in ("KEA4", "KEA6"):
                payload = normalize_kea_subnet(payload, iface_map)
            elif label == "RADVD":
                payload = normalize_radvd(payload, iface_map)
        ident = payload.get("name") or payload.get("description") or "<unnamed>"
        start = time.monotonic()
        try:
            res = await mgr.ensure(meta["state"], payload, check_mode=check_mode)
            dur_ms = int((time.monotonic() - start) * 1000)
            outcome = "ok"
            action = getattr(res, "action", None) or (res.get("action") if isinstance(res, dict) else "?")
            uuid = getattr(res, "uuid", None) or (res.get("uuid") if isinstance(res, dict) else None)
            changed = getattr(res, "changed", None) if not isinstance(res, dict) else res.get("changed")
            log.info(
                "[%s] %-8s changed=%-5s action=%s uuid=%s name=%r (%d ms)",
                label, "OK", str(changed), action, uuid, ident, dur_ms,
            )
        except OpnsenseError as exc:
            dur_ms = int((time.monotonic() - start) * 1000)
            outcome = "error"
            action = None
            uuid = None
            changed = None
            log.error("[%s] FAIL name=%r reason=%s (%d ms)", label, ident, exc, dur_ms)
        except Exception as exc:  # noqa: BLE001  defensive — never crash the catalog mid-apply
            dur_ms = int((time.monotonic() - start) * 1000)
            outcome = "error"
            action = None
            uuid = None
            changed = None
            log.exception("[%s] FAIL name=%r unexpected: %s (%d ms)", label, ident, exc, dur_ms)
        results.append(
            {
                "section": label,
                "name": ident,
                "outcome": outcome,
                "action": action,
                "uuid": uuid,
                "changed": changed,
                "duration_ms": dur_ms,
                "adr_ref": meta["ref"].get("adr"),
                "lib_manager": meta["ref"].get("lib_manager"),
                "ansible_module": meta["ref"].get("ansible_module"),
            },
        )


def summarize(results: list[dict[str, Any]]) -> None:
    print()
    print("=" * 100)
    print(f"{'SECTION':<10} {'NAME':<40} {'OUTCOME':<8} {'ACTION':<8} {'CHANGED':<8} {'ADR REF'}")
    print("=" * 100)
    for r in results:
        print(
            f"{r['section']:<10} {str(r['name'])[:39]:<40} "
            f"{r['outcome']:<8} {str(r['action'] or '-'):<8} "
            f"{str(r['changed']):<8} {r['adr_ref'] or '-'}"
        )
    print("=" * 100)
    total = len(results)
    errors = sum(1 for r in results if r["outcome"] == "error")
    changes = sum(1 for r in results if r["changed"])
    print(f"Total: {total}  Errors: {errors}  Changes: {changes}")


async def main_async(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.env)
    creds = load_credentials(args.env, secret_file=args.secret_file)

    log.info(
        "Target: https://%s:%s/ (verify_ssl=%s) — env=%s — check_mode=%s",
        creds["host"], creds["port"], creds["verify_ssl"], args.env, args.check,
    )

    aliases = catalog.get("opn_aliases", [])
    rules = catalog.get("opn_filter_rules", [])
    snat = catalog.get("opn_snat_rules", [])
    dnat = catalog.get("opn_dnat_rules", [])
    iface_map = catalog.get("opn_interface_map", {})

    # --only section scoping: apply just the requested catalog slice(s) so each
    # roadmap step touches only its own concern. Default (empty) = all sections.
    only: set[str] = {s.strip() for s in (args.only or "").split(",") if s.strip()}
    unknown = only - SECTION_GROUPS
    if unknown:
        raise SystemExit(
            f"--only: unknown section(s) {sorted(unknown)}; valid: {sorted(SECTION_GROUPS)}"
        )

    def want(group: str) -> bool:
        """True if this section group should run (no --only = run everything)."""
        return not only or group in only

    if only:
        log.info("[ONLY] restricting to sections: %s", sorted(only))

    results: list[dict[str, Any]] = []

    async with OpnsenseClient(
        host=creds["host"],
        port=creds["port"],
        key=creds["key"],
        secret=creds["secret"],
        verify_ssl=creds["verify_ssl"],
    ) as client:
        if want("fw"):
            await apply_section(FwAliasManager,     client, aliases, "ALIAS",  args.check, results)
            await apply_section(FwFilterManager,    client, rules,   "RULE",   args.check, results, iface_map=iface_map)
            await apply_section(FwSourceNatManager, client, snat,    "SNAT",   args.check, results, iface_map=iface_map)
            await apply_section(FwDnatManager,      client, dnat,    "DNAT",   args.check, results, iface_map=iface_map)

        # Unbound (split DNS) — opn_unbound block
        unbound = catalog.get("opn_unbound", {})
        if want("dns") and unbound.get("enabled"):
            host_overrides = [{"state": "present", **{k: v for k, v in h.items() if k != "ref"}} for h in unbound.get("host_overrides", [])]
            forwarders     = [{"state": "present", **{k: v for k, v in f.items() if k != "ref"}} for f in unbound.get("forwarders", [])]
            await apply_section(UbHostOverrideManager, client, host_overrides, "DNS_HO", args.check, results)
            await apply_section(UbForwardManager,      client, forwarders,     "DNS_FW", args.check, results)

        # Kea DHCPv4 — general settings (enable + interfaces) then subnets
        kea4 = catalog.get("opn_kea_dhcp4", {})
        if want("kea") and kea4.get("enabled"):
            await apply_kea_general(client, "kea/dhcpv4", kea4.get("general", {}), iface_map, "KEA4", args.check, results)
            subnets4 = [{"state": "present", **s} for s in kea4.get("subnets", [])]
            await apply_section(Kea4SubnetManager, client, subnets4, "KEA4", args.check, results, iface_map=iface_map)

        # Kea DHCPv6 — general settings then subnets (interface-bound)
        kea6 = catalog.get("opn_kea_dhcp6", {})
        if want("kea") and kea6.get("enabled"):
            await apply_kea_general(client, "kea/dhcpv6", kea6.get("general", {}), iface_map, "KEA6", args.check, results)
            subnets6 = [{"state": "present", **s} for s in kea6.get("subnets", [])]
            await apply_section(Kea6SubnetManager, client, subnets6, "KEA6", args.check, results, iface_map=iface_map)

        # Single reconfigure for both Kea services
        if want("kea") and (kea4.get("enabled") or kea6.get("enabled")):
            await reconfigure_kea(client, args.check, results)

        # Dnsmasq — singleton settings + sub-resources (lib-opnsense epic #65)
        # Order: settings first (must run before sub-resources can be applied
        # cleanly), then sub-resources, then service control last.
        dnsmasq = catalog.get("opn_dnsmasq", {})
        if want("dnsmasq") and dnsmasq.get("enabled"):
            settings = dnsmasq.get("settings")
            if settings:
                dn_mgr = DnsmasqSettingsManager(client)
                try:
                    res = await dn_mgr.ensure("present", settings, check_mode=args.check)
                    results.append({
                        "section": "DNSMASQ_SET", "name": "settings",
                        "outcome": "ok", "action": res.action, "uuid": None,
                        "changed": res.changed, "duration_ms": 0,
                        "adr_ref": "infra/0004", "lib_manager": "DnsmasqSettingsManager",
                        "ansible_module": None,
                    })
                except Exception as exc:  # noqa: BLE001
                    log.exception("[DNSMASQ_SET] FAIL: %s", exc)
                    results.append({
                        "section": "DNSMASQ_SET", "name": "settings",
                        "outcome": "error", "action": None, "uuid": None,
                        "changed": None, "duration_ms": 0,
                        "adr_ref": "infra/0004", "lib_manager": "DnsmasqSettingsManager",
                        "ansible_module": None,
                    })
            for sub_key, mgr_cls, label in (
                ("tags", DnsmasqTagManager, "DNSMASQ_TAG"),
                ("hosts", DnsmasqHostManager, "DNSMASQ_HOST"),
                ("ranges", DnsmasqRangeManager, "DNSMASQ_RANGE"),
                ("domains", DnsmasqDomainManager, "DNSMASQ_DOMAIN"),
                ("boots", DnsmasqBootManager, "DNSMASQ_BOOT"),
                ("options", DnsmasqOptionManager, "DNSMASQ_OPT"),
            ):
                entries = [{"state": e.get("state", "present"), **{k: v for k, v in e.items() if k not in ("state", "ref")}}
                           for e in dnsmasq.get(sub_key, [])]
                await apply_section(mgr_cls, client, entries, label, args.check, results, iface_map=iface_map)
            # Service control — only act if explicitly asked (state set in catalog)
            svc_state = dnsmasq.get("service_state")  # 'running' | 'stopped' | 'reconfigured'
            if svc_state:
                svc_mgr = DnsmasqServiceManager(client)
                try:
                    res = await svc_mgr.ensure(svc_state, check_mode=args.check)
                    results.append({
                        "section": "DNSMASQ_SVC", "name": f"ensure {svc_state}",
                        "outcome": "ok", "action": res.action, "uuid": None,
                        "changed": res.changed, "duration_ms": 0,
                        "adr_ref": "infra/0004", "lib_manager": "DnsmasqServiceManager",
                        "ansible_module": None,
                    })
                except Exception as exc:  # noqa: BLE001
                    log.exception("[DNSMASQ_SVC] FAIL: %s", exc)
                    results.append({
                        "section": "DNSMASQ_SVC", "name": f"ensure {svc_state}",
                        "outcome": "error", "action": None, "uuid": None,
                        "changed": None, "duration_ms": 0,
                        "adr_ref": "infra/0004", "lib_manager": "DnsmasqServiceManager",
                        "ansible_module": None,
                    })

        # radvd — per-interface RA entries + service control
        radvd = catalog.get("opn_radvd", {})
        if want("radvd") and radvd.get("enabled"):
            ra_entries = [{"state": e.get("state", "present"), **{k: v for k, v in e.items() if k not in ("state", "ref")}}
                          for e in radvd.get("entries", [])]
            await apply_section(RadvdEntryManager, client, ra_entries, "RADVD", args.check, results, iface_map=iface_map)
            svc_state = radvd.get("service_state")
            if svc_state:
                svc_mgr = RadvdServiceManager(client)
                try:
                    res = await svc_mgr.ensure(svc_state, check_mode=args.check)
                    results.append({
                        "section": "RADVD_SVC", "name": f"ensure {svc_state}",
                        "outcome": "ok", "action": res.action, "uuid": None,
                        "changed": res.changed, "duration_ms": 0,
                        "adr_ref": "infra/0004", "lib_manager": "RadvdServiceManager",
                        "ansible_module": None,
                    })
                except Exception as exc:  # noqa: BLE001
                    log.exception("[RADVD_SVC] FAIL: %s", exc)
                    results.append({
                        "section": "RADVD_SVC", "name": f"ensure {svc_state}",
                        "outcome": "error", "action": None, "uuid": None,
                        "changed": None, "duration_ms": 0,
                        "adr_ref": "infra/0004", "lib_manager": "RadvdServiceManager",
                        "ansible_module": None,
                    })

        # Local auth — WebGUI admin users + group hygiene. Auth changes apply
        # immediately (no reconfigure). Groups first (e.g. delete a stray group),
        # then users (membership carried by group_memberships = admin gid).
        auth = catalog.get("opn_auth", {})
        if want("auth") and auth:
            await apply_section(AuthGroupManager, client, auth.get("groups", []), "AUTH_GRP", args.check, results)
            users = [resolve_user_password(u) for u in auth.get("users", [])]
            await apply_section(AuthUserManager,  client, users,             "AUTH_USR", args.check, results)

    summarize(results)
    return 1 if any(r["outcome"] == "error" for r in results) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default=DEFAULT_ENV, help="Environment slug (default: test)")
    parser.add_argument("--check", action="store_true", help="Dry-run (no API writes)")
    parser.add_argument(
        "--only",
        default="",
        help=(
            "Comma-separated section groups to apply (default: all). "
            "Valid: fw, dns, kea, dnsmasq, radvd. "
            "E.g. --only fw applies only aliases+rules+NAT."
        ),
    )
    parser.add_argument("--secret-file", help="Override secret file path (for ad-hoc test FW credentials)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose / DEBUG logging")
    args = parser.parse_args()
    configure_logging(args.verbose)
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
