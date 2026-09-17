#!/usr/bin/env python3
"""Read a Trivy JSON report on stdin, print {image, critical, high} for the image
passed as argv[1]. Zero-safe: no vulns / malformed → zeros."""
import sys, json, collections
img = sys.argv[1] if len(sys.argv) > 1 else "?"
try:
    d = json.load(sys.stdin)
    vulns = [v for r in (d.get("Results") or []) for v in (r.get("Vulnerabilities") or [])]
    c = collections.Counter(v.get("Severity") for v in vulns)
except Exception:
    c = collections.Counter()
print(json.dumps({"image": img, "critical": c.get("CRITICAL", 0), "high": c.get("HIGH", 0)}))
