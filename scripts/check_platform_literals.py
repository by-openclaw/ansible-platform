#!/usr/bin/env python3
"""pre-commit: no platform identity literal in roles/ or playbooks/ — the deployment's domain and
organisation short-name come from the identity catalog (group_vars/all/deployment.yml) as
`platform_domain` / `platform_org`, never typed in a role, and never as a silent
`| default('...')` fallback (a missing value must fail, not become another deployment's identity).
Comments are ignored. Extend PATTERNS as further literal classes move into the catalog (zones,
host addresses)."""
import re, sys, pathlib

PATTERNS = {
    "domain literal": re.compile(r"by-research\.be"),
    "org literal": re.compile(r"(?<![a-z0-9_-])by-research(?![a-z0-9.-])"),
    "identity fallback": re.compile(r"default\((['\"])(by-research(\.be)?)\1\)"),
    "zone or aggregate CIDR": re.compile(r"\b10\.1\.\d{1,3}\.0/\d{1,2}\b|\bfd01:[0-9a-f]*::/\d{1,3}\b|\b100\.64\.0\.0/10\b"),
}
ROOTS = ("roles", "playbooks")
SUFFIXES = (".yml", ".yaml", ".j2")

def main() -> int:
    bad = []
    for root in ROOTS:
        for p in pathlib.Path(root).rglob("*"):
            if p.suffix not in SUFFIXES or "README" in p.name or "_archive" in p.parts:
                continue
            for n, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
                for kind, rx in PATTERNS.items():
                    if rx.search(code):
                        bad.append(f"{p}:{n}: {kind}: {line.strip()[:100]}")
    if bad:
        print("platform identity literals found (use platform_domain / platform_org, no fallback):")
        print("\n".join(bad))
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
