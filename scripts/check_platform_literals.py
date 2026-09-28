#!/usr/bin/env python3
"""pre-commit: no platform identity literal in roles/ or playbooks/ — the deployment's domain and
organisation short-name come from the identity catalog (group_vars/all/deployment.yml) as
`platform_domain` / `platform_org`, never typed in a role, and never as a silent
`| default('...')` fallback (a missing value must fail, not become another deployment's identity).
Comments are ignored. Extend PATTERNS as further literal classes move into the catalog (zones,
host addresses)."""
import re, sys, pathlib

PATTERNS = {
    # BOTH org names. Only "by-research" was listed, so a hardcoded by-systems.be in
    # roles/hardening's postfix template and a default('ops@by-systems.be') fallback
    # were invisible to the check meant to catch exactly that.
    "domain literal": re.compile(r"by-(research|systems)\.be"),
    "org literal": re.compile(r"(?<![a-zA-Z0-9_-])(?i:by-(research|systems))(?![a-zA-Z0-9.-])"),
    "identity fallback": re.compile(r"default\((['\"])(by-(research|systems)(\.be)?)\1\)"),
    # A missing inventory value must fail, never silently fall back to prod's.
    "env fallback": re.compile(r"platform_env\s*\|\s*default\("),
    "ssh port literal": re.compile(r"(?<![0-9])22222(?![0-9])"),
    "prod Vault path literal": re.compile(r"(?<!inventories)[\"'/ ]prod/[a-z{]"),   # inventories/prod = a folder
    "env-suffixed account literal": re.compile(r"\bsvc-[a-z0-9]+-(prod|test|dev|acc|staging)\b"),
    "machine name": re.compile(r"\b(lxc|vm|srv)-[a-z0-9-]+-[0-9]{2}\b"),
    "IPv4 literal": re.compile(r"\b(10|172|213)\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b"),
    # 10.6.x covers OOB and the switch fabric. They were missing from this pattern,
    # which is why five roles kept spelling them out long after the 10.1.x zones
    # were factored out — the guard simply never looked for them.
    "zone or aggregate CIDR": re.compile(
        r"\b10\.1\.\d{1,3}\.0/\d{1,2}\b|\b10\.6\.\d{1,3}\.0/\d{1,2}\b"
        r"|\bfd01:[0-9a-f]*::/\d{1,3}\b|\b100\.64\.0\.0/10\b"
    ),

    # Host addresses have a single source since 2026-09-24: the inventory carries
    # platform_host_v6 for every guest, and platform_zones carries gw4/gw6 per zone.
    # A literal here is a second copy that drifts — the firewall catalog held a SLAAC
    # address for CrowdSec while the host answered on its static one.
    "host IPv6 literal": re.compile(r"\bfd01:[0-9a-f]{1,4}::[0-9a-f:]{1,30}\b(?!/)"),

    # Access groups have a single source since 2026-09-24: platform_service_groups and the
    # platform_*_group vars in group_vars/all/identity.yml. The pattern deliberately lists the
    # real names instead of matching *-users/*-admins, because JumpServer owns an internal group
    # called bastion-admins that is NOT an identity-provider group — a blanket suffix rule would
    # flag it and teach people to ignore the guard.
    "access group literal": re.compile(
        r"[\"\']("
        r"diagrams-users|gitlab-users|gitlab-admins|harbor-users|harbor-admins|jitsi-users|"
        r"jumpserver-users|mailcow-users|grafana-admins|netbird-users|netbird-admins|"
        r"netbox-admins|nextcloud-users|nextcloud-admins|pbs-admins|pgadmin-admins|"
        r"proxmox-admins|seaweedfs-admins|traefik-admins|vault-admins|vaultwarden-admins|"
        r"verdaccio-users|platform-admins|infra-admins|ldap-search"
        r")[\"\']"
    ),
}

# Documented exceptions, per file and kind. vault_kv_map names two Vault PATHS that
# happen to contain the firewall's name (see the comment there), not host references.
EXEMPT = {
    "playbooks/vars/vault_kv_map.yml": ("machine name", "env-suffixed account literal"),   # legacy secret-file names
}

ROOTS = ("roles", "playbooks")
SUFFIXES = (".yml", ".yaml", ".j2", ".py")   # .py: scripts roles ship (files/) hardcoded a Vault URL

def main() -> int:
    bad = []
    for root in ROOTS:
        for p in pathlib.Path(root).rglob("*"):
            if p.suffix not in SUFFIXES or "README" in p.name or "_archive" in p.parts:
                continue
            # role metadata is never templated by Ansible, so an org name in an author
            # field is not a literal anyone can parameterise. Flagging it only teaches
            # people to ignore this check.
            if "meta" in p.parts:
                continue
            for n, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
                for kind, rx in PATTERNS.items():
                    if kind in EXEMPT.get(p.as_posix(), ()):
                        continue
                    if rx.search(code):
                        bad.append(f"{p}:{n}: {kind}: {line.strip()[:100]}")
    if bad:
        print("platform identity literals found (use platform_domain / platform_org, no fallback):")
        print("\n".join(bad))
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
