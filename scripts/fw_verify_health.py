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
  scripts/fw_verify_health.py --secret-file ~/.openclaw/workspace/infra/secrets/fabric/net-opnsense-prod-svc-ansible.json --expect-wan2
  scripts/fw_verify_health.py --secret-file ~/.openclaw/workspace/infra/secrets/fabric/net-opnsense-test-vm-opns-test-01.json --expect-wan2 --no-proximus
  # --expect-wan2       require Telenet WAN2 up with the env's OWN addresses (read from the ISP secret
  #                     file: net-isp-telenet.json for prod, net-isp-telenet-test.json for test — derived
  #                     from the creds file's `env`, or pass --isp-secret-file)
  # --no-proximus       the test FW keeps the single Proximus PPPoE account administratively down
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
    "OOB",
    "LAN_TRUNK",
    "MGMT",
    "DMZ",
    "SVC",
    "VPN",
    "IoT",
    "VoIP",
    "Storage",
    "Media",
    "GAMING",
    "CCTV",
    "FAB",  # fabric MGMT VLAN 600 (opt14, vtnet4) — seeded on prod (.2) and test (.3) since 2026-09
]
WAN1_IFACE = "WAN_PROXIMUS"  # checked unless --no-proximus (single PPPoE account: test keeps it down)
# Fallbacks only — --isp-secret-file (or the env-derived default) supplies the real addresses.
TELENET_V4_SUFFIX = ".222"
TELENET_V6_SUFFIX = "::5"


def load_telenet(secret_file: str, isp_secret_file: str | None) -> dict:
    """Expected Telenet WAN2 addresses for THIS env (prod .222/::5, test .220/::6)."""
    p = Path(isp_secret_file) if isp_secret_file else None
    if p is None:
        env = str(json.loads(Path(secret_file).read_text()).get("fields", {}).get("env", "prod"))
        p = Path(secret_file).parent / ("net-isp-telenet.json" if env == "prod" else f"net-isp-telenet-{env}.json")
    if not p.exists():
        return {}
    f = json.loads(p.read_text()).get("fields", {})
    return {"ipv4_address": f.get("ipv4_address"), "ipv6_address": f.get("ipv6_address"), "source": p.name}


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def load_creds(secret_file: str, host: str | None = None) -> dict:
    f = json.loads(Path(secret_file).read_text())["fields"]
    return {
        "base": f"https://{host or f['host']}:{int(f.get('port') or 443)}",
        "key": f["key"],
        "secret": f["secret"],
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
        req = urllib.request.Request(
            self.base + path, method=method, headers={"Authorization": self.auth}
        )
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
        print(
            f"{len(self.rows)} checks  |  {len(self.rows) - failed} pass  |  {failed} fail"
        )
        return 1 if failed else 0


def run(api: API, expect_wan2: bool, expect_proximus: bool = True, telenet: dict | None = None) -> int:
    g = Gate()
    telenet = telenet or {}

    # 1) Interfaces assigned & up
    try:
        info = api.get("/api/interfaces/overview/interfacesInfo")
        # interfacesInfo returns {"rows":[{description,device,status,addr4,...}], ...}
        rows = info.get("rows", info) if isinstance(info, dict) else info
        rows = rows if isinstance(rows, list) else []
        by_descr = {
            r.get("description"): r
            for r in rows
            if isinstance(r, dict) and r.get("description")
        }
    except Exception as e:  # noqa: BLE001
        g.check("interfaces overview reachable", False, str(e)[:24])
        return g.report()
    g.check("interfaces overview reachable", True, f"{len(by_descr)} assigned")
    for d in EXPECTED_IFACES:
        v = by_descr.get(d)
        up = bool(v) and str(v.get("status", "")).lower() == "up"
        g.check(f"iface {d} up", up, (v or {}).get("status", "absent"))

    # 2) WAN_PROXIMUS up + public-ish v4 (not RFC1918 / not empty) — unless --no-proximus
    if expect_proximus:
        wan1 = by_descr.get(WAN1_IFACE) or by_descr.get("WAN1") or {}
        g.check(
            f"iface {WAN1_IFACE} up",
            bool(wan1) and str(wan1.get("status", "")).lower() == "up",
            wan1.get("status", "absent"),
        )
        a4 = wan1.get("addr4") or wan1.get("ipaddr") or ""
        wan1_ok = (
            bool(a4)
            and not a4.startswith(("10.", "192.168.", "172."))
            and a4 not in ("pppoe", "dhcp")
        )
        g.check(f"{WAN1_IFACE} public IPv4", wan1_ok, a4 or "none")
    else:
        g.check(f"{WAN1_IFACE} (skipped: --no-proximus)", True, "admin down")

    # 3) WAN2 Telenet (gated)
    wan2 = by_descr.get("WAN_TELENET") or {}
    if expect_wan2:
        a4w2 = wan2.get("addr4") or wan2.get("ipaddr") or ""
        a6w2 = wan2.get("addr6") or wan2.get("ipaddrv6") or ""
        g.check(
            "WAN2 Telenet assigned & up",
            bool(wan2) and str(wan2.get("status", "")).lower() == "up",
            wan2.get("status", "absent"),
        )
        exp4, exp6 = telenet.get("ipv4_address"), telenet.get("ipv6_address")
        ok4 = (a4w2.split("/")[0] == exp4) if exp4 else a4w2.split("/")[0].endswith(TELENET_V4_SUFFIX)
        ok6 = (exp6.lower() in a6w2.lower()) if exp6 else (TELENET_V6_SUFFIX in a6w2)
        g.check(f"WAN2 Telenet IPv4 {exp4 or TELENET_V4_SUFFIX}", ok4, a4w2 or "none")
        g.check(f"WAN2 Telenet IPv6 {exp6 or TELENET_V6_SUFFIX}", ok6, a6w2 or "none")
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
        "unbound",
        "dnscrypt-proxy",
        "crowdsec",
        "kea-dhcp",
        "qemu-ga",
        "flowd_aggregate",
    ]
    try:
        svc = api.get("/api/core/service/search").get("rows", [])
        running = {}
        for r in svc:
            running[r.get("name")] = running.get(r.get("name"), False) or str(
                r.get("running")
            ) in ("1", "True", "true")
        for name in required_services:
            label = "reporting (flowd_aggregate)" if name == "flowd_aggregate" else name
            g.check(
                f"service {label} running",
                running.get(name, False),
                "running" if running.get(name) else "DOWN",
            )
    except Exception as e:  # noqa: BLE001
        g.check("service list reachable", False, str(e)[:24])

    return g.report()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--secret-file", required=True)
    p.add_argument(
        "--host",
        default=None,
        help="override FW host/IP (e.g. OOB 10.6.239.196 if the secret is stale)",
    )
    p.add_argument(
        "--expect-wan2",
        action="store_true",
        help="require Telenet WAN2 up with this env's own addresses",
    )
    p.add_argument(
        "--no-proximus",
        action="store_true",
        help="skip the WAN_PROXIMUS checks (test FW: single PPPoE account stays down)",
    )
    p.add_argument(
        "--isp-secret-file",
        default=None,
        help="Telenet ISP secret file (fields ipv4_address/ipv6_address); default derived from the creds file's env",
    )
    args = p.parse_args()
    telenet = load_telenet(args.secret_file, args.isp_secret_file) if args.expect_wan2 else {}
    if telenet.get("source"):
        print(f"[info] Telenet expectations from {telenet['source']}: {telenet.get('ipv4_address')} / {telenet.get('ipv6_address')}")
    sys.exit(
        run(
            API(load_creds(args.secret_file, args.host)),
            args.expect_wan2,
            expect_proximus=not args.no_proximus,
            telenet=telenet,
        )
    )


if __name__ == "__main__":
    main()
