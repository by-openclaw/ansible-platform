#!/usr/bin/env python3
"""Firewall catalog lint (naming/0003). Input: JSON {aliases, rules, single_family_interfaces}.
Checks present entries only:
  §3  every source/destination net + port field is an alias (or any / (self)); ipprotocol ∈ inet|inet6|inet46
  §1a a family-suffixed alias (host4_/host6_/net4_/net6_/grp_net4_/grp_net6_) must have its pair
  §4  a rule with a source/destination port must be protocol tcp, udp or tcp/udp (OPNsense rejects the rest)
  twins: an inet (inet6) rule on a dual-stack interface must have its inet6 (inet) twin —
         same description with the family marker removed — unless the interface is single-family
Exit 1 with the list of violations."""
import json
import re
import sys

SUF = re.compile(r"^(host|net|grp_net)([46])_(.+)$")
KEYWORDS = {"any", "(self)", ""}


def base(desc):
    t = re.sub(r"\s*\(v[46]\)\s*$", "", desc)
    t = re.sub(r"\s+v[46]\)$", ")", t)
    t = re.sub(r"\s+v[46]$", "", t)
    return t.strip()


def pair(name):
    m = SUF.match(name)
    return f"{m.group(1)}{'6' if m.group(2) == '4' else '4'}_{m.group(3)}" if m else None


def main(path):
    d = json.load(open(path))
    aliases = {a["name"]: a for a in d["aliases"] if a.get("state", "present") == "present"}
    rules = [r for r in d["rules"] if r.get("state", "present") == "present"]
    single_if = set(d.get("single_family_interfaces") or [])
    names = set(aliases) | KEYWORDS
    v = []
    for a in aliases:
        p = pair(a)
        if p and p not in aliases:
            v.append(f"§1a alias '{a}' is family-suffixed but '{p}' is missing (single-family scope → unsuffixed name)")
    fams = {}
    for r in rules:
        desc = r.get("description", "?")
        for k in ("source_net", "destination_net", "destination_port", "source_port"):
            val = str(r.get(k, "") or "")
            if val not in names:
                v.append(f"§3 rule '{desc}': {k}='{val}' is not an alias")
        proto = r.get("ipprotocol", "inet")
        if proto not in ("inet", "inet6", "inet46"):
            v.append(f"rule '{desc}': ipprotocol '{proto}' invalid")
        # §4 OPNsense rejects ports on anything but tcp/udp ("Destination ports are only
        # valid for tcp or udp type rules") — catch it here, not at apply time.
        l4 = str(r.get("protocol", "any") or "any").lower()
        if any(str(r.get(k, "") or "") for k in ("destination_port", "source_port")) and l4 not in ("tcp", "udp", "tcp/udp"):
            v.append(f"§4 rule '{desc}': has a port alias but protocol='{l4}' (ports need tcp, udp or tcp/udp)")
        fams.setdefault(base(desc), {})[proto] = r
    for b, byfam in fams.items():
        if "inet46" in byfam or {"inet", "inet6"} <= set(byfam):
            continue
        proto, r = next(iter(byfam.items()))
        if r.get("interface") in single_if:
            continue
        nets = [str(r.get(k, "") or "") for k in ("source_net", "destination_net")]
        if any(SUF.match(n) for n in nets):   # dual-stack scope → twin required
            v.append(f"twin: '{r.get('description')}' ({proto}, if={r.get('interface')}) has no {'inet6' if proto == 'inet' else 'inet'} twin")
    print(f"catalog_lint: aliases={len(aliases)} rules={len(rules)} violations={len(v)}")
    for x in v:
        print("  - " + x)
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
