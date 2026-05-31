#!/usr/bin/env python3
# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/ansible-platform
"""Validate the live OPNsense test FW state against the catalog.

Pulls non-invasive diagnostic evidence from the FW:
    - ARP table (IPv4 neighbors)
    - NDP table (IPv6 neighbors)
    - Routing table
    - Firewall state table (live flows, labelled with rule UUIDs)
    - Kea v4 + v6 lease tables
    - radvd service status + entries
    - Interface name map

Compares it against the catalog (aliases for host4_probe_*/host6_probe_* +
radvd entries) and reports per-VLAN PASS/FAIL with the evidence quoted.

Designed to be the ground-truth check after every catalog apply, and the
source of evidence rows in docs/compliance/opnsense-test-fw.md.
"""
from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from opnsense.client import OpnsenseClient

VLANS = ["mgmt", "dmz", "svc", "vpn", "iot", "voip", "storage", "media", "gaming", "cctv"]


def load_expected(catalog_path: Path) -> dict[str, dict[str, str]]:
    cat = yaml.safe_load(catalog_path.read_text())
    aliases = cat.get("opn_aliases", []) or cat.get("opn_alias", [])
    iface_map = cat.get("opn_interface_map", {})
    expected: dict[str, dict[str, str]] = {v: {} for v in VLANS}
    for a in aliases:
        if not isinstance(a, dict):
            continue
        name = a.get("name", "")
        for v in VLANS:
            if name == f"host4_probe_{v}":
                expected[v]["v4"] = str(a.get("content", "")).strip()
            elif name == f"host6_probe_{v}":
                expected[v]["v6"] = str(a.get("content", "")).strip()
    radvd_entries = (cat.get("opn_radvd", {}) or {}).get("entries", [])
    expected_radvd_slots: set[str] = set()
    for e in radvd_entries:
        iface = e.get("interface", "")
        slot = iface_map.get(iface, iface)
        if str(e.get("enabled", "0")) == "1":
            expected_radvd_slots.add(slot)
    return {"vlans": expected, "radvd_slots": expected_radvd_slots, "iface_map": iface_map}


async def pull_live(c: OpnsenseClient) -> dict[str, Any]:
    arp = await c.get("diagnostics/interface/get_arp")
    ndp = await c.get("diagnostics/interface/get_ndp")
    iface_names = await c.get("diagnostics/interface/getInterfaceNames")
    states = await c.post("diagnostics/firewall/queryStates", {"current": 1, "rowCount": 500})
    leases4 = await c.post("kea/leases4/search", {"current": 1, "rowCount": 200})
    leases6 = await c.post("kea/leases6/search", {"current": 1, "rowCount": 200})
    radvd_status = await c.get("radvd/service/status")
    radvd_entries = await c.post("radvd/settings/searchEntry", {"current": 1, "rowCount": 200})
    return {
        "arp": arp,
        "ndp": ndp,
        "iface_names": iface_names,
        "states": states,
        "leases4": leases4,
        "leases6": leases6,
        "radvd_status": radvd_status,
        "radvd_entries": radvd_entries.get("rows", radvd_entries),
    }


def index_arp(arp: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for e in arp or []:
        ip = e.get("ip")
        if ip:
            out[ip] = e
    return out


def index_ndp(ndp: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for e in ndp or []:
        ip = e.get("ip")
        if ip:
            out[ip.lower()] = e
    return out


def rule_uuids_in_states(states: Any) -> set[str]:
    rows = states.get("rows") if isinstance(states, dict) else states
    out: set[str] = set()
    for r in rows or []:
        label = r.get("label", "")
        if label and len(label) == 36 and label.count("-") == 4:
            out.add(label)
    return out


def render_row(label: str, status: str, evidence: str) -> str:
    icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "INFO": "·"}.get(status, "?")
    return f"  {icon} {label:<42} {status:<5} {evidence}"


def validate(expected: dict[str, Any], live: dict[str, Any]) -> int:
    arp_idx = index_arp(live["arp"])
    ndp_idx = index_ndp(live["ndp"])
    iface_names: dict[str, str] = live["iface_names"]
    radvd_slots_live = {e.get("interface") for e in live["radvd_entries"] if str(e.get("enabled", "0")) == "1"}
    rule_uuids_active = rule_uuids_in_states(live["states"])

    fail = 0
    print("=" * 100)
    print("FW VALIDATION — vm-opns-test-01 against catalog (test env)")
    print("=" * 100)

    # radvd service + entry coverage
    print("\n[radvd]")
    status = live["radvd_status"].get("status", "?")
    if status == "running":
        print(render_row("service status", "PASS", f"status={status}"))
    else:
        print(render_row("service status", "FAIL", f"status={status} (expected running)"))
        fail += 1

    expected_slots = expected["radvd_slots"]
    missing_radvd = expected_slots - radvd_slots_live
    extra_radvd = radvd_slots_live - expected_slots
    if not missing_radvd and not extra_radvd:
        print(render_row("entries match catalog", "PASS", f"{len(expected_slots)} slots enabled: {sorted(expected_slots)}"))
    else:
        if missing_radvd:
            print(render_row("entries missing on FW", "FAIL", f"{sorted(missing_radvd)}"))
            fail += 1
        if extra_radvd:
            print(render_row("entries extra on FW", "WARN", f"{sorted(extra_radvd)}"))

    # Per-VLAN LXC reachability
    print("\n[per-VLAN LXC reachability — ARP (v4) + NDP (v6) from FW]")
    for v in VLANS:
        exp = expected["vlans"].get(v, {})
        ip4 = exp.get("v4")
        ip6 = exp.get("v6", "").lower()
        slot = expected["iface_map"].get(v, v)
        iface_label = iface_names.get(slot, slot)
        print(f"\n  VLAN={v} slot={slot} ({iface_label})")
        if ip4:
            hit = arp_idx.get(ip4)
            if hit:
                print(render_row(f"  v4 probe {ip4}", "PASS", f"mac={hit.get('mac')} intf={hit.get('intf')}"))
            else:
                print(render_row(f"  v4 probe {ip4}", "FAIL", "no ARP entry — LXC unreachable from FW"))
                fail += 1
        else:
            print(render_row("  v4 probe", "WARN", "no host4_probe_* alias in catalog"))
        if ip6:
            hit = ndp_idx.get(ip6)
            if hit:
                print(render_row(f"  v6 probe {ip6}", "PASS", f"mac={hit.get('mac')} intf={hit.get('intf')}"))
            else:
                print(render_row(f"  v6 probe {ip6}", "FAIL", "no NDP entry — LXC v6 unreachable from FW"))
                fail += 1
        else:
            print(render_row("  v6 probe", "WARN", "no host6_probe_* alias in catalog"))

    # Rule activity (state table shows recent flows + matching rule UUIDs)
    print("\n[rule activity — state table samples]")
    print(render_row("active flows in state table", "INFO", f"{len(rule_uuids_active)} distinct rule UUIDs hit"))

    # Kea lease summary (we expect 0 since LXCs are static)
    print("\n[Kea leases — expected 0 because LXCs use static addressing]")
    n4 = (live["leases4"] or {}).get("total", 0)
    n6 = (live["leases6"] or {}).get("total", 0)
    label_kea = "no Kea v4/v6 leases (consistent with static LXC config)"
    if n4 == 0 and n6 == 0:
        print(render_row("Kea lease tables empty", "PASS", label_kea))
    else:
        print(render_row("Kea lease tables non-empty", "INFO", f"v4={n4} v6={n6} (lib gaps will land here)"))

    print("\n" + "=" * 100)
    if fail == 0:
        print("RESULT: all checks PASS — FW matches catalog. Evidence captured.")
    else:
        print(f"RESULT: {fail} FAIL(s) — FW state diverges from catalog. Investigate.")
    print("=" * 100)
    return 0 if fail == 0 else 1


async def main_async(args: argparse.Namespace) -> int:
    sec = json.loads(Path(args.secret_file).read_text())["fields"]
    catalog_path = Path(__file__).resolve().parents[1] / "inventories" / args.env / "group_vars" / "opnsense.yml"
    expected = load_expected(catalog_path)
    async with OpnsenseClient(host=sec["host"], port=sec["port"], key=sec["key"], secret=sec["secret"], verify_ssl=False) as c:
        live = await pull_live(c)
    if args.json:
        print(json.dumps({"expected": {k: (sorted(v) if isinstance(v, set) else v) for k, v in expected.items()}, "live_summary": {
            "arp_count": len(live["arp"] or []),
            "ndp_count": len(live["ndp"] or []),
            "radvd_status": live["radvd_status"].get("status"),
            "radvd_entries": len(live["radvd_entries"] or []),
            "states_total": (live["states"] or {}).get("total", 0),
            "leases4_total": (live["leases4"] or {}).get("total", 0),
            "leases6_total": (live["leases6"] or {}).get("total", 0),
        }}, indent=2))
        return 0
    return validate(expected, live)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", default="test")
    parser.add_argument("--secret-file", required=True)
    parser.add_argument("--json", action="store_true", help="Emit raw summary JSON (skip pretty validation)")
    args = parser.parse_args()
    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
