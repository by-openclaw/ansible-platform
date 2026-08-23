#!/usr/bin/env python3
"""Pass 2 — OPNsense firewall PRUNE AUDIT (reverse of fw_apply_direct).

fw_apply_direct.py is additive: it makes the live firewall a SUPERSET of the
catalog but never detects live rules that are NOT in the catalog. This script is
the reverse diff — it flags LIVE aliases / filter rules / D-NAT / source-NAT that
the Ansible catalog does not declare (out-of-band drift), so the live firewall can
be proven equal to `inventories/<env>/group_vars/opnsense.yml`.

Read-only: reports orphans, deletes nothing. Exit 0 = clean (live == catalog),
1 = orphans found.

  python3 scripts/fw_prune_audit.py --env prod --secret-file <api-creds.json>

Objects OPNsense (or a plugin) manages itself are NOT catalog-manageable and are
excluded by design — see EXCLUDE_* below.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

# --- Non-manageable live objects (never in the fw catalog, not drift) ----------
# OPNsense auto-generated aliases (per-interface networks) + built-in system
# aliases, and plugin-owned dynamic aliases (CrowdSec blocklists). These exist on
# every device and cannot be expressed in opn_aliases.
EXCLUDE_ALIAS_PREFIX = ("__",)
EXCLUDE_ALIAS_EXACT = {"bogons", "bogonsv6", "sshlockout", "virusprot"}
EXCLUDE_ALIAS_REGEX = re.compile(r"^crowdsec", re.IGNORECASE)
# Auto-generated / system filter + NAT rules (no description or a system one).
EXCLUDE_RULE_SUBSTR = (
    "Anti-Lockout",
    "anti-lockout",
    "Automatically generated",
    "Default allow",
    "IPsec",
    "OpenVPN",
)


def excluded_alias(name: str) -> bool:
    return (
        name.startswith(EXCLUDE_ALIAS_PREFIX)
        or name in EXCLUDE_ALIAS_EXACT
        or bool(EXCLUDE_ALIAS_REGEX.match(name))
    )


def excluded_rule(desc: str) -> bool:
    return (not desc) or any(s in desc for s in EXCLUDE_RULE_SUBSTR)


def load_creds(secret_file: str) -> dict:
    return json.loads(Path(secret_file).read_text())["fields"]


def api_rows(host: str, key: str, secret: str, path: str) -> list[dict]:
    out = subprocess.run(
        ["curl", "-sk", "-u", f"{key}:{secret}", f"https://{host}{path}"],
        capture_output=True,
        text=True,
    ).stdout
    try:
        return json.loads(out).get("rows", [])
    except (ValueError, AttributeError):
        return []


def audit_section(title, rows, name_field, catset, is_excluded, orphans_out) -> int:
    orphans = []
    for r in rows:
        name = (
            r.get(name_field) or r.get("description") or r.get("descr") or ""
        ).strip()
        if is_excluded(name):
            continue
        if name not in catset:
            orphans.append(
                f"      if={r.get('interface', '-')} act={r.get('action', '-')} "
                f"dport={r.get('destination_port', '-')} :: {name or '(no description)'}"
            )
    print(f"  {title}: {len(rows)} live, {len(orphans)} orphan(s) not in catalog")
    for o in orphans:
        print(o)
    orphans_out[title] = len(orphans)
    return len(orphans)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="OPNsense firewall prune audit (live vs catalog)"
    )
    ap.add_argument("--env", default="prod")
    ap.add_argument("--secret-file", required=True)
    args = ap.parse_args()

    creds = load_creds(args.secret_file)
    host, key, secret = creds["host"], creds["key"], creds["secret"]
    catalog = yaml.safe_load(
        (
            REPO_ROOT / "inventories" / args.env / "group_vars" / "opnsense.yml"
        ).read_text()
    )

    def descs(section: str, field: str) -> set[str]:
        return {
            (r.get(field) or "").strip()
            for r in (catalog.get(section) or [])
            if r.get(field)
        }

    cat_alias = {
        r["name"].strip() for r in (catalog.get("opn_aliases") or []) if r.get("name")
    }
    cat_filter = descs("opn_filter_rules", "description")
    cat_dnat = descs("opn_dnat_rules", "descr")
    cat_snat = descs("opn_snat_rules", "descr") | descs("opn_snat_rules", "description")

    print(
        "================ FW PRUNE AUDIT (live rules NOT in catalog) ================"
    )
    counts: dict[str, int] = {}
    total = 0
    total += audit_section(
        "Aliases",
        api_rows(host, key, secret, "/api/firewall/alias/search_item"),
        "name",
        cat_alias,
        excluded_alias,
        counts,
    )
    total += audit_section(
        "Filter rules",
        api_rows(host, key, secret, "/api/firewall/filter/search_rule"),
        "description",
        cat_filter,
        excluded_rule,
        counts,
    )
    total += audit_section(
        "D-NAT",
        api_rows(host, key, secret, "/api/firewall/d_nat/search_rule"),
        "descr",
        cat_dnat,
        excluded_rule,
        counts,
    )
    total += audit_section(
        "Source-NAT",
        api_rows(host, key, secret, "/api/firewall/source_nat/search_rule"),
        "descr",
        cat_snat,
        excluded_rule,
        counts,
    )
    print("=" * 76)
    verdict = (
        "CLEAN — live == catalog (no out-of-band drift)"
        if total == 0
        else "DRIFT — review above"
    )
    print(f"  TOTAL ORPHANS: {total}  ->  {verdict}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
