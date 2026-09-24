#!/usr/bin/env python3
"""Fail a commit that makes a task loop over a register --check never fills.

Why this exists
---------------
`command`, `shell`, `script` and `uri` do not run under `--check` unless the task
says `check_mode: false`. A skipped task still registers a result, but an empty
one. A later task that loops over `<register>.stdout_lines` then ends the play
with "No last item, sequence was empty" — and the dry-run reports a broken play
rather than the truth, which is that a dry-run cannot know.

`when: not ansible_check_mode` does NOT save the task: Ansible evaluates a task's
loop expression BEFORE its when. The fix is to parse the register into a fact
with a safe default and loop over that fact.

What is deliberately NOT flagged
--------------------------------
`changed_when` / `failed_when` on the registering task itself. A skipped task
never evaluates its own conditions, so those are safe.

Usage: check_loop_on_skipped_register.py [files...]   (default: roles/ playbooks/)
"""

from __future__ import annotations

import pathlib
import re
import sys

SKIPS_IN_CHECK = ("command", "shell", "script", "uri")
MODULE_RE = re.compile(r"^\s*(?:ansible\.builtin\.)?(" + "|".join(SKIPS_IN_CHECK) + r"):\s*$")
REGISTER_RE = re.compile(r"^\s*register:\s*(\w+)\s*$")
LOOP_RE = re.compile(r"^\s*(?:loop|with_items|with_list):")
SAFE = ("default(", "is defined", "ansible_check_mode")
FIELDS = r"(stdout|stdout_lines|results|json|content)"


def scan(path: pathlib.Path) -> list[tuple[int, str, str, str]]:
    try:
        lines = path.read_text(errors="ignore").split("\n")
    except OSError:
        return []

    registers: dict[str, tuple[str, int]] = {}
    pending: tuple[str, int] | None = None
    for i, line in enumerate(lines):
        module = MODULE_RE.match(line)
        if module:
            pending = (module.group(1), i)
            continue
        found = REGISTER_RE.match(line)
        if found and pending:
            window = "\n".join(lines[max(0, pending[1] - 6) : i + 14])
            if "check_mode: false" not in window:
                registers[found.group(1)] = (pending[0], i + 1)
            pending = None

    hits = []
    for i, line in enumerate(lines):
        if not LOOP_RE.match(line):
            continue
        if any(token in line for token in SAFE):
            continue
        for name, (module, declared) in registers.items():
            if re.search(rf"\b{re.escape(name)}\.{FIELDS}\b", line):
                hits.append((i + 1, name, f"{module} at line {declared}", line.strip()))
    return hits


def main(argv: list[str]) -> int:
    if argv:
        targets = [pathlib.Path(a) for a in argv if a.endswith((".yml", ".yaml"))]
    else:
        targets = [
            p
            for root in ("roles", "playbooks")
            for p in pathlib.Path(root).rglob("*.yml")
            if pathlib.Path(root).is_dir()
        ]

    failures = 0
    for path in targets:
        if not path.is_file():
            continue
        for line_no, name, origin, text in scan(path):
            failures += 1
            print(f"{path}:{line_no}: loops over '{name}', registered by a {origin}")
            print(f"    {text}")
            print(
                "    --check skips that module, so the register is empty here and the loop"
                " ends the play.\n"
                "    Parse it into a fact with a safe default first, then loop over the fact."
                " `when: not ansible_check_mode` does not help: the loop is evaluated first.\n"
            )

    if failures:
        print(f"{failures} loop(s) depend on a register that --check leaves empty.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
