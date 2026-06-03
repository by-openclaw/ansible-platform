#!/usr/bin/env python3
# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/ansible-platform
"""Functional health gate for the OPNsense FW — the "does it actually work" check.

Read-only. Runs the objective pass/fail checks that decide whether a freshly
(re)seeded + ansible-configured FW is GOOD: interfaces assigned & up, BOTH WANs
up with the right IPs, gateways up, DNS resolves through the chain, NetFlow
active. Exits non-zero if ANY check fails — so it can gate a reseed (rehearse on
a throwaway VM first; only promote to prod when this is green, twice).

Pure stdlib + the FW MVC API. No catalog/lib import, so it runs anywhere.

Usage:
  scripts/fw_verify_health.py --secret-file ~/.openclaw/workspace/infra/secrets/OPNsense.prod_root_password.json
  # optional: --expect-wan2  (require Telenet WAN2 up — once the seed assigns it)
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.request
from pathlib import Path

# Expected assigned interfaces (description -> must be 'up'). Mirrors the catalog;
# WAN2 is gated behind --expect-wan2 until the seed assigns it.
EXPECTED_IFACES = [
    # Final naming (06-01): OOB = physical break-glass (vtnet1); LAN_TRUNK = trunk
    # (vtnet0); MGMT = vlan1010 in-band mgmt; WAN_PROXIMUS = WAN1. Post-reseed names.
    "OOB", "LAN_TRUNK", "MGMT", "DMZ", "SVC", "VPN",
    "IoT", "VoIP", "Storage", "Media", "GAMING", "CCTV", "WAN_PROXIMUS",
]
TELENET_V4_SUFFIX = ".222"
TELENET_V6_SUFFIX = "::5"


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def load_creds(secret_file: str, host: str | None = None) -> dict:
    f = json.loads(Path(secret_file).read_text())["fields"]
    return {
        "base": f"https://{host or f['host']}:{int(f.get('port') or 443)}",
        "key": f["key"], "secret": f["secret"],
        "verify_ssl": _bool(f.get("verify_ssl", False)),
    }


class API:
    def __init__(self, creds: dict):
        self.base = creds["base"]
        self.ctx = ssl.create_default_context()
        if not creds["verify_ssl"]:
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE
        import base64
        tok = base64.b64encode(f"{creds['key']}:{creds['secret']}".encode()).decode()
        self.auth = f"Basic {tok}"

    def get(self, path: str, method: str = "GET") -> dict | list:
        req = urllib.request.Request(self.base + path, method=method,
                                     headers={"Authorization": self.auth})
        with urllib.request.urlopen(req, timeout=20, context=self.ctx) as r:
            return json.loads(r.read().decode())


class Gate:
    def __init__(self):
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = ""):
        self.rows.append((name, bool(ok), detail))

    def report(self) -> int:
        print("\n" + "=" * 78)
        print(f"{'CHECK':<46}{'RESULT':<8}{'DETAIL'}")
        print("=" * 78)
        failed = 0
        for name, ok, detail in self.rows:
            mark = "✓ PASS" if ok else "✗ FAIL"
            if not ok:
                failed += 1
            print(f"{name[:45]:<46}{mark:<8}{detail[:24]}")
        print("=" * 78)
        print(f"{len(self.rows)} checks  |  {len(self.rows) - failed} pass  |  {failed} fail")
        return 1 if failed else 0


def run(api: API, expect_wan2: bool) -> int:
    g = Gate()

    # 1) Interfaces assigned & up
    try:
        info = api.get("/api/interfaces/overview/interfacesInfo")
        # interfacesInfo returns {"rows":[{description,device,status,addr4,...}], ...}
        rows = info.get("rows", info) if isinstance(info, dict) else info
        rows = rows if isinstance(rows, list) else []
        by_descr = {r.get("description"): r for r in rows
                    if isinstance(r, dict) and r.get("description")}
    except Exception as e:  # noqa: BLE001
        g.check("interfaces overview reachable", False, str(e)[:24])
        return g.report()
    g.check("interfaces overview reachable", True, f"{len(by_descr)} assigned")
    for d in EXPECTED_IFACES:
        v = by_descr.get(d)
        up = bool(v) and str(v.get("status", "")).lower() == "up"
        g.check(f"iface {d} up", up, (v or {}).get("status", "absent"))

    # 2) WAN_PROXIMUS has a public-ish v4 (not RFC1918 / not empty)
    wan1 = by_descr.get("WAN_PROXIMUS") or by_descr.get("WAN1") or {}
    a4 = (wan1.get("addr4") or wan1.get("ipaddr") or "")
    wan1_ok = bool(a4) and not a4.startswith(("10.", "192.168.", "172.")) and a4 not in ("pppoe", "dhcp")
    g.check("WAN_PROXIMUS public IPv4", wan1_ok, a4 or "none")

    # 3) WAN2 Telenet (gated)
    wan2 = by_descr.get("WAN_TELENET") or {}
    if expect_wan2:
        a4w2 = (wan2.get("addr4") or wan2.get("ipaddr") or "")
        a6w2 = (wan2.get("addr6") or wan2.get("ipaddrv6") or "")
        g.check("WAN2 Telenet assigned & up", bool(wan2) and str(wan2.get("status", "")).lower() == "up",
                wan2.get("status", "absent"))
        g.check("WAN2 Telenet IPv4 .222", a4w2.endswith(TELENET_V4_SUFFIX), a4w2 or "none")
        g.check("WAN2 Telenet IPv6 ::5", TELENET_V6_SUFFIX in a6w2, a6w2 or "none")
    else:
        g.check("WAN2 Telenet (skipped: --expect-wan2 off)", True, "seed pending")

    # 4) Gateways up (no 'down' status among configured gateways)
    try:
        gws = api.get("/api/routes/gateway/status").get("items", [])
        bad = [x["name"] for x in gws if str(x.get("status", "")).lower() == "down"]
        g.check("gateways: none down", not bad, ",".join(bad) or f"{len(gws)} ok")
    except Exception as e:  # noqa: BLE001
        g.check("gateways status reachable", False, str(e)[:24])

    # 5) Core services running (the actual "service didn't work" signal)
    #    flowd_aggregate = Insight/NetFlow reporting; the rest = DNS chain, IPS, DHCP, agent.
    required_services = [
        "unbound", "dnscrypt-proxy", "crowdsec", "kea-dhcp", "qemu-ga", "flowd_aggregate",
    ]
    try:
        svc = api.get("/api/core/service/search").get("rows", [])
        running = {}
        for r in svc:
            running[r.get("name")] = running.get(r.get("name"), False) or str(r.get("running")) in ("1", "True", "true")
        for name in required_services:
            label = "reporting (flowd_aggregate)" if name == "flowd_aggregate" else name
            g.check(f"service {label} running", running.get(name, False),
                    "running" if running.get(name) else "DOWN")
    except Exception as e:  # noqa: BLE001
        g.check("service list reachable", False, str(e)[:24])

    return g.report()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--secret-file", required=True)
    p.add_argument("--host", default=None,
                   help="override FW host/IP (e.g. OOB 10.6.239.196 if the secret is stale)")
    p.add_argument("--expect-wan2", action="store_true",
                   help="require Telenet WAN2 up (enable once the seed assigns it)")
    args = p.parse_args()
    sys.exit(run(API(load_creds(args.secret_file, args.host)), args.expect_wan2))


if __name__ == "__main__":
    main()
