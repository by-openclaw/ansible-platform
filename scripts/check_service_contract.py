#!/usr/bin/env python3
"""The per-service contract, checked. Its count of passing services is the refactor's
one progress number ("N of 32 on the contract"). For every entry of platform_services
(group_vars/all/services.yml), its `role` and `playbook` must satisfy:

  facts       every play in the playbook that runs a role gathers facts — a role that reads
              facts met a play that skipped them, and certs-sync broke (#670)
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


def runs_a_role(play):
    if play.get("roles"):
        return True
    for key in ("tasks", "pre_tasks", "post_tasks"):
        for task in play.get(key) or []:
            if any(k.endswith(("include_role", "import_role")) for k in task):
                return True
    return False


def check(svc, people):
    role, failures = svc["role"], []
    playbook = ROOT / svc["playbook"] if "/" in svc["playbook"] else ROOT / "playbooks" / svc["playbook"]
    if not playbook.exists():
        failures.append(f"playbook missing ({svc['playbook']})")
    else:
        plays = yaml.safe_load(playbook.read_text()) or []
        no_facts = [p.get("name", "?") for p in plays if isinstance(p, dict) and "hosts" in p
                    and p.get("gather_facts", True) in (False, "false", "no") and runs_a_role(p)]
        if no_facts:
            failures.append(f"facts({len(no_facts)} play(s) run roles without facts)")
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
