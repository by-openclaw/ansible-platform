#!/usr/bin/env python3
"""Emit host OS posture JSON from env vars set by os.yml (keeps the shell line short)."""
import json, os
print(json.dumps({
    "security_updates": int(os.environ.get("SEC", "0") or 0),
    "total_updates": int(os.environ.get("TOT", "0") or 0),
    "fixable_cve_pkgs": int(os.environ.get("CVE", "0") or 0),
    "reboot_required": os.environ.get("RB", "no"),
    "cves": os.environ.get("CVELIST", "").split(),
}))
