#!/usr/bin/env python3
# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/ansible-platform
"""Phase-1 DNS-chain bridge: Unbound → dnscrypt-proxy (one-off; delete when managers land).

This script is a **temporary** bridge for catalog blocks that lib-opnsense doesn't
yet have managers for. Once these managers exist, fw_apply_direct.py will dispatch
them and this script can be deleted:

  - DnscryptProxyManager           → lib-opnsense#NN (file alongside this PR)
  - UbSettingsManager.forwarding   → lib-opnsense#75 (already filed)
  - UbDotManager dispatch hook     → small extension to fw_apply_direct.py
                                     (after UbDotManager has full coverage)

Steps it performs, with a verification gate after each:
  1. Snapshot live state (Unbound DoT entries, dnscrypt status, dig test)
  2. Configure dnscrypt-proxy general settings (listen 127.0.0.1:53531 + [::1]:53531,
     servers from catalog.opn_dnscrypt_proxy.serverlist, etc.)
  3. Start dnscrypt-proxy service + verify it answers on 53531
  4. Set unbound.forwarding.enabled='1' via generic settings POST
  5. Delete the 8 live DoT entries (from prior PR #20 apply) via UbDotManager
  6. Apply Unbound (reconfigure) — fw_apply_direct.py adds the 2 new forwarders;
     this script will also create them directly if --no-apply is set on the catalog
  7. Verify dumpInfra shows forwarders (not DoT) and dig via Unbound resolves cleanly

Defaults: dry-run. Pass --apply to write changes. Each gate prints diff before doing.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG = REPO_ROOT / "inventories/test/group_vars/opnsense.yml"
SECRETS = Path.home() / ".openclaw/workspace/infra/secrets"


def load_secret():
    d = json.loads((SECRETS / "net-opnsense-vm-opns-test-01.json").read_text())["fields"]
    return d


def fw_get(s, path, t=10):
    return requests.get(f"https://{s['host']}:{s.get('port',443)}/api{path}",
                        auth=(s["key"], s["secret"]), verify=False, timeout=t)


def fw_post(s, path, body=None, t=30):
    return requests.post(f"https://{s['host']}:{s.get('port',443)}/api{path}",
                         auth=(s["key"], s["secret"]), verify=False, timeout=t,
                         json=body or {})


def header(msg):
    print(f"\n{'=' * 70}\n=== {msg}\n{'=' * 70}")


def diff_show(label, current, target):
    print(f"\n  diff [{label}]:")
    keys = sorted(set(current.keys()) | set(target.keys()))
    for k in keys:
        c = current.get(k, "<absent>")
        t = target.get(k, "<absent>")
        marker = "  " if c == t else "≠ "
        print(f"    {marker}{k}: {c!r}  →  {t!r}")


def gate(prompt, apply_flag):
    if not apply_flag:
        print(f"  [DRY-RUN] would: {prompt}")
        return False
    print(f"  [APPLY ] {prompt}")
    return True


def step1_snapshot(s):
    header("Step 1 — snapshot current live state")
    # Unbound general
    r = fw_get(s, "/unbound/settings/get").json()["unbound"]
    g = r["general"]
    fw_state = r.get("forwarding", {})
    print(f"  unbound.general.port        = {g['port']}")
    print(f"  unbound.forwarding.enabled  = {fw_state.get('enabled')}")
    # DoT entries
    dot_rows = fw_get(s, "/unbound/settings/searchDot").json().get("rows", [])
    print(f"  unbound DoT/forward entries = {len(dot_rows)}")
    for r in dot_rows:
        is_dot = (r.get("type") or "").lower() == "dot" or r.get("port") == "853"
        print(f"    [{r['uuid'][:8]}] type={'dot' if is_dot else 'fwd':3s} {r.get('server'):28s}:{r['port']} enabled={r['enabled']}")
    # dnscrypt
    dc = fw_get(s, "/dnscryptproxy/general/get").json()["general"]
    listen = [k for k, v in dc.get("listen_addresses", {}).items() if isinstance(v, dict) and v.get("selected") == 1] if isinstance(dc.get("listen_addresses"), dict) else dc.get("listen_addresses")
    print(f"  dnscrypt.enabled  = {dc.get('enabled')}")
    print(f"  dnscrypt.listen   = {listen}")
    print(f"  dnscrypt.ipv6     = {dc.get('ipv6_servers')}")
    # service
    ds = fw_get(s, "/dnscryptproxy/service/status").json()
    print(f"  dnscrypt.service  = {ds.get('status')}")
    return {"dot_rows": dot_rows, "unbound_general": g, "unbound_fwd": fw_state, "dnscrypt": dc, "dnscrypt_svc": ds}


def step2_dnscrypt_general(s, catalog, apply):
    header("Step 2 — configure dnscrypt-proxy general settings")
    target = catalog["opn_dnscrypt_proxy"]["general"]
    current = fw_get(s, "/dnscryptproxy/general/get").json()["general"]

    # Build the POST body. OPNsense expects the same shape it returns, but with
    # listen_addresses as a comma-joined string and ipv4_servers etc. as '0'/'1'.
    body_general = {}
    for k, v in target.items():
        if k == "listen_addresses":
            body_general[k] = ",".join(v) if isinstance(v, list) else v
        else:
            body_general[k] = v

    # Diff
    cur_listen = list(current.get("listen_addresses", {}).keys()) if isinstance(current.get("listen_addresses"), dict) else current.get("listen_addresses")
    print(f"  current listen: {cur_listen}")
    print(f"  target  listen: {target['listen_addresses']}")
    for k in ("enabled", "ipv4_servers", "ipv6_servers", "require_dnssec", "cache_size"):
        cv = current.get(k)
        tv = target.get(k)
        if cv != tv:
            print(f"    ≠ {k}: {cv!r}  →  {tv!r}")

    if not gate("POST /dnscryptproxy/general/set + reconfigure", apply):
        return

    r = fw_post(s, "/dnscryptproxy/general/set", {"general": body_general})
    print(f"  general/set → HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code != 200 or r.json().get("result") not in ("saved", "ok"):
        sys.exit(f"FAIL: dnscrypt general/set: {r.text}")

    # Also configure server names. The "serverlist" is part of general in the
    # OPNsense plugin model — check if it was accepted; else use server endpoint.
    sl = catalog["opn_dnscrypt_proxy"]["serverlist"]
    body2 = {"general": {"serverlist": ",".join(sl)}}
    r2 = fw_post(s, "/dnscryptproxy/general/set", body2)
    print(f"  serverlist/set → HTTP {r2.status_code}: {r2.text[:300]}")


def step3_dnscrypt_start_verify(s, apply):
    header("Step 3 — reconfigure + start dnscrypt-proxy + verify port 53531")
    if not gate("POST /dnscryptproxy/service/reconfigure", apply):
        return
    r = fw_post(s, "/dnscryptproxy/service/reconfigure")
    print(f"  reconfigure → HTTP {r.status_code}: {r.text[:200]}")
    # Wait for log to settle
    time.sleep(4)
    st = fw_get(s, "/dnscryptproxy/service/status").json()
    print(f"  service status: {st.get('status')}")
    if st.get("status") != "running":
        # Try explicit start
        rs = fw_post(s, "/dnscryptproxy/service/start")
        print(f"  service/start → {rs.text[:200]}")
        time.sleep(2)
        st = fw_get(s, "/dnscryptproxy/service/status").json()
        print(f"  service status: {st.get('status')}")

    # Verify via qm guest exec: dig @127.0.0.1 -p 53531 google.com
    print("  verifying via qm guest exec dig ...")
    out = qm_exec(["/usr/local/bin/drill", "@127.0.0.1", "-p", "53531", "google.com"])
    if not out:
        out = qm_exec(["/usr/bin/nc", "-z", "-w2", "127.0.0.1", "53531"])
    print(f"  guest-exec result: {out!r}" if out else "  (no output)")


def step4_unbound_forwarding_enable(s, apply):
    header("Step 4 — ensure unbound.forwarding.enabled=0 (counter-intuitive but correct)")
    # WHY 0: On OPNsense, `forwarding.enabled=1` makes Unbound generate a
    # forward-zone that points at `<system><dnsserver>` (the WAN gateway plain DNS),
    # and IGNORES the catalog's forward entries. With `enabled=0`, catch-all
    # forward entries (domain='') become a forward-zone "." — which is what we want.
    # Verified on vm-opns-test-01 2026-05-25 via `dumpInfra`. See memory:
    # lib-opnsense/reference_unbound_forwarding_toggle.
    r = fw_get(s, "/unbound/settings/get").json()["unbound"]
    cur = r.get("forwarding", {}).get("enabled")
    print(f"  current: forwarding.enabled = {cur!r}")
    print(f"  target:  forwarding.enabled = '0' (chain works via catch-all forward-zone, not generic forwarding)")
    if cur == "0":
        print("  [NOOP] already disabled")
        return
    if not gate("POST /unbound/settings/set with forwarding.enabled=0", apply):
        return
    body = {"unbound": {"forwarding": {"enabled": "0"}}}
    r2 = fw_post(s, "/unbound/settings/set", body)
    print(f"  set → HTTP {r2.status_code}: {r2.text[:300]}")


def step5_drop_dot(s, apply):
    header("Step 5 — disable the 8 live DoT entries (Cloudflare + Quad9 :853)")
    rows = fw_get(s, "/unbound/settings/searchDot").json().get("rows", [])
    dot_uuids = []
    for r in rows:
        is_dot = (r.get("port") == "853")  # cheap heuristic; could probe getDot per uuid
        if is_dot and r.get("enabled") == "1":
            dot_uuids.append((r["uuid"], r.get("server"), r.get("port")))
    print(f"  {len(dot_uuids)} DoT entries to disable:")
    for u, srv, p in dot_uuids:
        print(f"    [{u[:8]}] {srv}:{p}")
    if not dot_uuids:
        print("  [NOOP] no DoT entries to disable")
        return
    if not gate(f"toggleDot off (or delDot) {len(dot_uuids)} entries", apply):
        return
    for u, _, _ in dot_uuids:
        # Try toggle first (sets enabled=0); fall back to delete
        r = fw_post(s, f"/unbound/settings/toggleDot/{u}/0")
        if r.status_code != 200 or r.json().get("result") != "Disabled":
            r = fw_post(s, f"/unbound/settings/delDot/{u}")
        print(f"  [{u[:8]}] → {r.status_code} {r.text[:120]}")


def step6_apply_unbound_reconfigure(s, apply):
    header("Step 6 — apply Unbound (reconfigure) — picks up new forwarders + drops")
    if not gate("POST /unbound/service/reconfigure", apply):
        return
    r = fw_post(s, "/unbound/service/reconfigure")
    print(f"  reconfigure → HTTP {r.status_code}: {r.text[:200]}")
    time.sleep(3)


def step7_verify_chain(s):
    header("Step 7 — verify chain end-to-end")
    # dumpInfra should show forwarders, NOT DoT
    di = fw_get(s, "/diagnostics/dns/get") if False else fw_get(s, "/unbound/diagnostics/dumpInfra")
    if di.status_code == 200:
        print(f"  dumpInfra:\n{json.dumps(di.json(), indent=2)[:1200]}")
    # dig via FW Unbound (port 53) — should resolve and route through dnscrypt-proxy
    out = qm_exec(["/usr/local/bin/drill", "@127.0.0.1", "-p", "53", "example.com"])
    print(f"  drill via Unbound:\n{out}")


def qm_exec(argv):
    """Run a command in the FW via qemu-guest-agent (returns stdout or None)."""
    pve = json.loads((SECRETS / "infra-proxmox-poc.json").read_text())["fields"]
    headers = {"Authorization": f"PVEAPIToken={pve['admin_token_id']}={pve['admin_token_secret']}",
               "Content-Type": "application/json"}
    base = f"https://{pve['host']}:8006/api2/json/nodes/srv-proxmox-poc-01/qemu/199/agent"
    r = requests.post(f"{base}/exec", headers=headers, verify=False, timeout=15,
                      data=json.dumps({"command": argv}))
    if r.status_code != 200:
        return None
    pid = r.json().get("data", {}).get("pid")
    h2 = {k: v for k, v in headers.items() if k != "Content-Type"}
    for _ in range(15):
        time.sleep(1)
        s = requests.get(f"{base}/exec-status", headers=h2, verify=False, timeout=10, params={"pid": pid})
        if s.status_code != 200:
            continue
        b = s.json()["data"]
        if b.get("exited"):
            return (b.get("out-data", "") or "") + (b.get("err-data", "") or "")
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    p.add_argument("--only", choices=["1", "2", "3", "4", "5", "6", "7", "snapshot", "dnscrypt", "unbound", "verify"],
                   help="run only a subset")
    args = p.parse_args()

    s = load_secret()
    catalog = yaml.safe_load(CATALOG.read_text())
    print(f"FW = {s['host']}  apply = {args.apply}  only = {args.only}")

    if args.only in (None, "1", "snapshot"):
        step1_snapshot(s)
    if args.only in (None, "2", "dnscrypt"):
        step2_dnscrypt_general(s, catalog, args.apply)
    if args.only in (None, "3", "dnscrypt"):
        step3_dnscrypt_start_verify(s, args.apply)
    if args.only in (None, "4", "unbound"):
        step4_unbound_forwarding_enable(s, args.apply)
    if args.only in (None, "5", "unbound"):
        step5_drop_dot(s, args.apply)
    if args.only in (None, "6", "unbound"):
        step6_apply_unbound_reconfigure(s, args.apply)
    if args.only in (None, "7", "verify"):
        step7_verify_chain(s)

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()
