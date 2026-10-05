#!/usr/bin/env python3
"""Provisioning is Ansible: modules and plain commands, no program written inside a task,
a unit or a role's files. This guard counts what still is one, per file, and lets the counts
only go down. It is the progress number of that refactor and the gate that stops a new one.

Counted, in roles/ and playbooks/ (archives excluded):

  shell_tasks          a task whose module is shell (ansible.builtin.shell) — a script in YAML
  script_module        a task whose module is script — it runs a program shipped by the role
  raw_module           a task whose module is raw
  inline_interpreters  a line that hands a program to an interpreter: sh -c, bash -c,
                       python -c, php -r, perl -e, ruby -e (in a task or in a unit's command),
                       or a task whose argument list does the same ([..., python3, -c, ...])
  script_files         a program under a role's files/ or templates/ (.sh .py .pl .rb .go .jq
                       .php, also as .j2). APP_CONFIG names the files that are an application's
                       own configuration in that application's language, with the reason.

The user module's `shell:` (a login shell) is an argument of that module, not a task: only
task-level keys are read.

Usage: scripts/check_no_embedded_scripts.py [--ratchet | --update | --list CATEGORY]
  (no flag)  print the counts.
  --ratchet  (pre-commit, CI) exit 1 when a file's count is above scripts/embedded_scripts_baseline.json;
             when counts went down, rewrite the baseline and exit 1 once so that it is committed.
  --update   rewrite the baseline to what is found (only ever used to lower it).
  --list     print every occurrence of one category.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINE = ROOT / "scripts" / "embedded_scripts_baseline.json"
TREES = ("roles", "playbooks")
EXCLUDED_PARTS = ("playbooks/archive/", "playbooks/_archive/")
STRUCTURE = ("tasks", "pre_tasks", "post_tasks", "handlers", "block", "rescue", "always")
MODULES = {
    "shell_tasks": ("shell", "ansible.builtin.shell"),
    "script_module": ("script", "ansible.builtin.script"),
    "raw_module": ("raw", "ansible.builtin.raw"),
}
INLINE = re.compile(r"(?<![\w-])(?:(?:ba)?sh -c|python3? -c|php -r|perl -e|ruby -e)(?![\w-])")
# The same thing written as an argument list: an interpreter followed by its "program follows" flag.
ARGV_INTERPRETERS = {"sh": "-c", "bash": "-c", "python": "-c", "python3": "-c", "php": "-r", "perl": "-e", "ruby": "-e"}
SCRIPT_SUFFIXES = (".sh", ".py", ".pl", ".rb", ".go", ".jq", ".php")
# An application's own configuration, written in the language that application reads.
APP_CONFIG = {
    "roles/gitlab/templates/gitlab.rb.j2": "GitLab's configuration file is Ruby (gitlab.rb)",
    "roles/netbox/templates/extra.py.j2": "NetBox's configuration file is Python (extra.py)",
}
CATEGORIES = (*MODULES, "inline_interpreters", "script_files")


class _Loader(yaml.SafeLoader):
    """Reads any playbook: an unknown tag (!vault, !unsafe) is taken as its plain value."""


def _any_tag(loader, _suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_mapping(node)


_Loader.add_multi_constructor("!", _any_tag)


def _in_scope(path: pathlib.Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return not any(part in rel + "/" for part in EXCLUDED_PARTS)


def _yaml_files():
    for tree in TREES:
        for path in sorted((ROOT / tree).rglob("*.yml")):
            if _in_scope(path) and "/files/" not in path.as_posix() and "/templates/" not in path.as_posix():
                yield path


def _tasks(node):
    """Every task-level mapping reachable through plays, blocks and handlers."""
    if isinstance(node, list):
        for item in node:
            if isinstance(item, dict):
                yield item
                for key in STRUCTURE:
                    yield from _tasks(item.get(key))


def _argv_runs_a_program(argv: list) -> bool:
    words = [str(word) for word in argv]
    return any(
        ARGV_INTERPRETERS.get(word.rsplit("/", 1)[-1]) == following
        for word, following in zip(words, words[1:])
    )


def scan() -> dict[str, dict[str, int]]:
    found: dict[str, dict[str, int]] = {category: {} for category in CATEGORIES}

    def add(category: str, path: pathlib.Path, count: int = 1) -> None:
        rel = path.relative_to(ROOT).as_posix()
        found[category][rel] = found[category].get(rel, 0) + count

    for path in _yaml_files():
        text = path.read_text(encoding="utf-8")
        try:
            document = yaml.load(text, Loader=_Loader)  # noqa: S506 - a SafeLoader subclass
        except yaml.YAMLError as exc:
            raise SystemExit(f"{path.relative_to(ROOT)}: not readable as YAML ({exc})") from exc
        for task in _tasks(document):
            for category, keys in MODULES.items():
                if any(key in task for key in keys):
                    add(category, path)
            for value in task.values():
                argv = value.get("argv") if isinstance(value, dict) else None
                if isinstance(argv, list) and _argv_runs_a_program(argv):
                    add("inline_interpreters", path)
    for tree in TREES:
        for path in sorted((ROOT / tree).rglob("*")):
            if not path.is_file() or not _in_scope(path):
                continue
            rel = path.relative_to(ROOT).as_posix()
            name = path.name[:-3] if path.name.endswith(".j2") else path.name
            in_role_payload = "/files/" in rel or "/templates/" in rel
            if in_role_payload and name.endswith(SCRIPT_SUFFIXES) and rel not in APP_CONFIG:
                add("script_files", path)
            if path.suffix in (".yml", ".j2"):
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                hits = sum(1 for line in lines if not line.lstrip().startswith("#") and INLINE.search(line))
                if hits:
                    add("inline_interpreters", path, hits)
    return found


def totals(found: dict[str, dict[str, int]]) -> dict[str, int]:
    return {category: sum(found[category].values()) for category in CATEGORIES}


def _write_baseline(found: dict[str, dict[str, int]]) -> None:
    BASELINE.write_text(json.dumps({c: dict(sorted(found[c].items())) for c in CATEGORIES}, indent=2) + "\n", encoding="utf-8")


def ratchet(found: dict[str, dict[str, int]], baseline: dict[str, dict[str, int]]) -> tuple[list[str], bool]:
    """(what rose, whether anything went down)."""
    rose, fell = [], False
    for category in CATEGORIES:
        allowed = baseline.get(category, {})
        for rel, count in sorted(found[category].items()):
            if count > allowed.get(rel, 0):
                rose.append(f"{category}: {rel} has {count}, the baseline allows {allowed.get(rel, 0)}")
        for rel, count in allowed.items():
            if found[category].get(rel, 0) < count:
                fell = True
    return rose, fell


def main(argv: list[str]) -> int:
    found = scan()
    if "--update" in argv:
        _write_baseline(found)
    if "--list" in argv:
        category = argv[argv.index("--list") + 1]
        for rel, count in sorted(found[category].items()):
            print(f"{count:3d}  {rel}")
        return 0
    if "--ratchet" in argv:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        rose, fell = ratchet(found, baseline)
        if rose:
            print("New embedded script(s) — provisioning is Ansible modules and plain commands:")
            for line in rose:
                print("  " + line)
            return 1
        if fell:
            _write_baseline(found)
            print("Fewer embedded scripts than the baseline: scripts/embedded_scripts_baseline.json was lowered — stage it.")
            return 1
        return 0
    print(" · ".join(f"{category} {count}" for category, count in totals(found).items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
