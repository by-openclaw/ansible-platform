#!/usr/bin/env python3
"""Which plays must be dry-run for a given change?

A change to a shared role reaches every play that includes it — directly, through another role's
meta/dependencies, or through include_role/import_role anywhere in its tasks. Validating a sample
is how a fleet-wide edit (#519, 93 files) broke a play nobody re-ran (#520, the firewall's catalog
guard). This prints the complete set instead.

    scripts/impacted_plays.py                 # plays impacted by the working tree vs origin/main
    scripts/impacted_plays.py <git-range>     # e.g. HEAD~5..HEAD, or a merge commit
    scripts/impacted_plays.py --files a b c   # explicit paths
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLE_REF = re.compile(
    r"""(?x)
    (?: ^\s*-\s*role:\s*['"]?(?P<a>[a-zA-Z0-9_.-]+)
      | ^\s*-\s*['"]?(?P<b>[a-zA-Z0-9_-]+)['"]?\s*$
      | (?:include_role|import_role):\s*$
      | ^\s*name:\s*['"]?(?P<c>[a-zA-Z0-9_-]+)['"]?\s*$
    )"""
)


def changed_files(args: list[str]) -> list[str]:
    if args and args[0] == "--files":
        return args[1:]
    rng = args[0] if args else "origin/main...HEAD"
    out = subprocess.run(["git", "diff", "--name-only", rng], cwd=ROOT, capture_output=True, text=True)
    files = [f for f in out.stdout.split() if f]
    if not files:  # fall back to the working tree
        out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
        files = [line[3:] for line in out.stdout.splitlines() if line[3:]]
    return files


def roles_used_by(path: Path) -> set[str]:
    """Roles a playbook or task file references, in any of Ansible's spellings."""
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return set()
    used: set[str] = set()
    used.update(re.findall(r"^\s*-\s*role:\s*['\"]?([a-zA-Z0-9_.-]+)", text, re.M))
    used.update(re.findall(r"(?:include_role|import_role):\s*\n\s*name:\s*['\"]?([a-zA-Z0-9_.-]+)", text))
    # bare list entries under `roles:`
    for block in re.findall(r"^\s*roles:\s*\n((?:\s*-\s*[^\n]+\n)+)", text, re.M):
        for line in block.splitlines():
            m = re.match(r"\s*-\s*['\"]?([a-zA-Z0-9_-]+)['\"]?\s*$", line)
            if m:
                used.add(m.group(1))
    used.update(re.findall(r"^\s*-\s*import_playbook:\s*(\S+)", text, re.M))
    return {u for u in used if u}


def role_closure(seed: set[str]) -> set[str]:
    """Roles that (transitively) pull in any seed role, via meta/dependencies or include/import."""
    reverse: dict[str, set[str]] = {}
    for role_dir in (ROOT / "roles").iterdir():
        if not role_dir.is_dir():
            continue
        refs: set[str] = set()
        for f in list(role_dir.rglob("*.yml")) + list(role_dir.rglob("*.yaml")):
            refs |= roles_used_by(f)
        for r in refs:
            reverse.setdefault(r, set()).add(role_dir.name)
    closure, frontier = set(seed), set(seed)
    while frontier:
        nxt: set[str] = set()
        for r in frontier:
            for parent in reverse.get(r, set()):
                if parent not in closure:
                    closure.add(parent)
                    nxt.add(parent)
        frontier = nxt
    return closure


def main(argv: list[str]) -> int:
    files = changed_files(argv)
    if not files:
        print("no changed files")
        return 0
    seed_roles = {f.split("/")[1] for f in files if f.startswith("roles/") and len(f.split("/")) > 2}
    changed_playbooks = {f for f in files if f.startswith("playbooks/") and f.endswith((".yml", ".yaml"))}
    inventory_touched = [f for f in files if f.startswith("inventories/")]
    roles = role_closure(seed_roles)

    impacted: dict[str, str] = {}
    for pb in sorted((ROOT / "playbooks").rglob("*.yml")):
        rel = str(pb.relative_to(ROOT))
        if "_archive" in rel:
            continue
        if rel in changed_playbooks:
            impacted[rel] = "the playbook itself changed"
            continue
        used = roles_used_by(pb)
        hit = sorted(used & roles)
        if hit:
            impacted[rel] = "uses " + ", ".join(hit[:4]) + ("…" if len(hit) > 4 else "")

    print(f"changed files: {len(files)} | seed roles: {len(seed_roles)} | roles reached: {len(roles)}")
    if inventory_touched:
        print(f"inventory touched ({len(inventory_touched)}): every play that reads those group_vars is impacted")
    print(f"\nplays to dry-run ({len(impacted)}):")
    for pb, why in sorted(impacted.items()):
        print(f"  {pb:<44} {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
