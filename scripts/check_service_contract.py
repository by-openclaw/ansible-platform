#!/usr/bin/env python3
"""The per-service contract, checked. Its count of passing services is the refactor's
one progress number ("N of 32 on the contract"). For every entry of platform_services
(group_vars/all/services.yml), its `role` and `playbook` must satisfy:

  facts       a play that skips fact gathering reaches no role that reads facts without
              gathering them itself (through includes and meta dependencies) — certs-sync
              broke exactly so (#670)
  data        the playbook carries no literal data in play vars (only connection settings
              and references) — values live in the inventory, never in a playbook
  meta        the service role has no meta dependencies — composition belongs in the
              playbook, where it is seen; a hidden one ran the docker firewall inside a
              certificate copy
  containers  no docker_container / docker compose in the role's tasks — containers go
              through roles/service_scaffold (containers:) or roles/compose_stack
  timers      no systemd timer written by the role — scheduled work is roles/host_job
  mailbox     no Mailcow mailbox write — the one writer is roles/mailbox
  database    no CREATE DATABASE / ROLE / USER — the one writer is roles/postgres_db
  people      no platform_people username in the role — people come from people.yml

Usage: scripts/check_service_contract.py [--strict | --ratchet] [service ...]
One line per service. --strict: exit 1 when any named (or any) service fails.
--ratchet (pre-commit): exit 1 when a service listed in scripts/service_contract_passing.txt
fails — a service that reached the contract cannot silently fall off it. A service PR
that brings one onto the contract adds its name to that file.
"""
import pathlib, re, sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
PASSING = ROOT / "scripts/service_contract_passing.txt"
INV = ROOT / "inventories/prod/group_vars/all"
MODULE = r"^\s+(?:community\.docker\.)?{}:\s*$"
CHECKS = {
    "containers": [re.compile(MODULE.format(m), re.M) for m in ("docker_container", "docker_compose", "docker_compose_v2")]
                  + [re.compile(r"docker[ -]compose\b.*\b(up|down|pull)\b")],
    "timers": [re.compile(r"/etc/systemd/system/[^\"'\s]+\.timer")],
    "mailbox": [re.compile(r"/api/v1/(add|edit|delete)/mailbox")],
    "database": [re.compile(r"\bCREATE\s+(DATABASE|ROLE|USER)\b", re.I)],
}


def strip_comments(text):
    return "\n".join(line.split(" #")[0] if not line.lstrip().startswith("#") else "" for line in text.splitlines())


def role_files(role, parts):
    base = ROOT / "roles" / role
    for part in parts:
        yield from sorted((base / part).rglob("*")) if (base / part).is_dir() else []


FACT = re.compile(r"\bansible_(facts|default_ipv[46]|distribution\w*|os_family|virtualization_\w+|mounts|memtotal_mb"
                  r"|processor\w*|hostname|fqdn|nodename|lsb|kernel\w*|architecture|interfaces|all_ipv[46]_addresses"
                  r"|machine\w*|pkg_mgr|service_mgr|date_time|devices|product_\w+|system_vendor|dns)\b")
ROLE_REF = re.compile(r"(?:include_role|import_role):\s*\n\s+name:\s*([\w.-]+)")
_facts_cache = {}


def play_roles(play):
    names = [r if isinstance(r, str) else r.get("role", "") for r in play.get("roles") or []]
    for key in ("tasks", "pre_tasks", "post_tasks"):
        for task in play.get(key) or []:
            for k, v in task.items():
                if k.endswith(("include_role", "import_role")) and isinstance(v, dict):
                    names.append(v.get("name", ""))
    return [n for n in names if n and "{" not in n]


def needs_facts(role, seen=()):
    """A role reads facts and does not gather them itself — directly, or through a role it
    includes or depends on."""
    if role in _facts_cache or role in seen:
        return _facts_cache.get(role, False)
    base = ROOT / "roles" / role
    text = "\n".join(strip_comments(f.read_text()) for f in role_files(role, ["tasks", "defaults", "vars", "templates", "handlers"])
                     if f.is_file() and f.suffix in (".yml", ".yaml", ".j2"))
    gathers = "ansible.builtin.setup" in text or re.search(r"^\s+setup:\s*$", text, re.M)
    result = bool(FACT.search(text)) and not gathers
    meta = base / "meta/main.yml"
    deps = ((yaml.safe_load(meta.read_text()) or {}).get("dependencies") or []) if meta.exists() else []
    refs = [d["role"] if isinstance(d, dict) else str(d) for d in deps] + ROLE_REF.findall(text)
    result = result or any(needs_facts(r, seen + (role,)) for r in refs if r != role and (ROOT / "roles" / r).is_dir())
    _facts_cache[role] = result
    return result


def literal_data(value):
    """True when a play var holds data rather than a reference: a plain scalar, or any
    literal inside a list/dict. A string with a template in it is a reference."""
    if isinstance(value, str):
        return "{{" not in value
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, list):
        return any(literal_data(v) for v in value)
    if isinstance(value, dict):
        return any(literal_data(v) for v in value.values())
    return False


def check(svc, people):
    role, failures = svc["role"], []
    playbook = ROOT / svc["playbook"] if "/" in svc["playbook"] else ROOT / "playbooks" / svc["playbook"]
    if not playbook.exists():
        failures.append(f"playbook missing ({svc['playbook']})")
    else:
        plays = [p for p in (yaml.safe_load(playbook.read_text()) or []) if isinstance(p, dict) and "hosts" in p]
        no_facts = sorted({r for p in plays if p.get("gather_facts", True) in (False, "false", "no")
                           for r in play_roles(p) if needs_facts(r)})
        if no_facts:
            failures.append("facts(" + ",".join(no_facts) + " in a play without facts)")
        data = sorted({k for p in plays for k, v in (p.get("vars") or {}).items()
                       if not k.startswith("ansible_") and literal_data(v)})
        if data:
            failures.append("data(" + ",".join(data) + ")")
    meta = ROOT / "roles" / role / "meta/main.yml"
    deps = ((yaml.safe_load(meta.read_text()) or {}).get("dependencies") or []) if meta.exists() else []
    if deps:
        failures.append("meta(" + "+".join(d["role"] if isinstance(d, dict) else str(d) for d in deps) + ")")
    tasks = "\n".join(strip_comments(f.read_text()) for f in role_files(role, ["tasks"]) if f.suffix in (".yml", ".yaml"))
    for name, patterns in CHECKS.items():
        hits = sum(len(p.findall(tasks)) for p in patterns)
        if hits:
            failures.append(f"{name}({hits})")
    body = "\n".join(strip_comments(f.read_text()) for f in role_files(role, ["tasks", "defaults", "vars", "templates"])
                     if f.is_file() and f.suffix in (".yml", ".yaml", ".j2"))
    named = sorted(u for u in people if re.search(rf"(?<![\w-]){re.escape(u)}(?![\w-])", body))
    if named:
        failures.append("people(" + ",".join(named) + ")")
    return failures


def main(argv):
    strict, ratchet = "--strict" in argv, "--ratchet" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    services = yaml.safe_load((INV / "services.yml").read_text())["platform_services"]
    people = {p["username"] for p in yaml.safe_load((INV / "people.yml").read_text())["platform_people"]}
    rows, passing = [], 0
    for svc in services:
        if wanted and svc["name"] not in wanted:
            continue
        failures = check(svc, people)
        passing += not failures
        rows.append((svc["name"], svc["role"], "PASS" if not failures else "FAIL", " ".join(failures)))
    for name, role, result, why in sorted(rows, key=lambda r: (r[2] != "PASS", r[0])):
        print(f"{name:14s} {role:18s} {result}  {why}")
    print(f"\non the contract: {passing} of {len(rows)}")
    if ratchet:
        held = {line.split("#")[0].strip() for line in PASSING.read_text().splitlines()} - {""}
        fallen = sorted(held & {r[0] for r in rows if r[2] == "FAIL"})
        new = sorted({r[0] for r in rows if r[2] == "PASS"} - held)
        if new:
            print("now passing, add to " + PASSING.name + ": " + " ".join(new))
        if fallen:
            print("FELL OFF THE CONTRACT: " + " ".join(fallen))
            return 1
    return 1 if strict and passing < len(rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
