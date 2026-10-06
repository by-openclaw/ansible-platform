#!/usr/bin/env python3
"""Fail when a change removes an inventory variable that roles or playbooks still read.

A variable that disappears from the inventory while code still reads it falls back to a role
default without a word. On 2026-10-05 an unrelated edit replaced the `seaweedfs_mirrors` block
instead of adding below it: the role then configured no mirror, the job on the host became an
orphan, and nothing said so.

What is compared: the top-level variable names under inventories/<env>/group_vars and host_vars,
at the base of the change and in the working tree. The base is INVENTORY_GUARD_BASE when set, the
first parent of HEAD in CI (the commit a pull request is merged onto, or the previous main), and
otherwise the merge base with origin/main.

A removal is accepted when no file under roles/ or playbooks/ names the variable any more, or when
scripts/inventory_removed_vars_allowed.yml lists it with the reason (an inventory override dropped
because the role default is now the right value).
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWED = ROOT / "scripts" / "inventory_removed_vars_allowed.yml"
VARS_FILE = re.compile(r"^inventories/([^/]+)/(?:group_vars|host_vars)/.+\.ya?ml$")
READ_BY = ("roles", "playbooks")
CODE = {".yml", ".yaml", ".j2", ".py"}   # a README that names a variable does not read it
ENCRYPTED = "$ANSIBLE_VAULT"


class _Loader(yaml.SafeLoader):
    """Inventory files may carry tags the safe loader does not know (!vault, !unsafe)."""


_Loader.add_multi_constructor("!", lambda loader, suffix, node: None)


def names_in(text: str) -> set[str]:
    """Top-level variable names of one inventory file (none for an encrypted or broken file)."""
    if text.lstrip().startswith(ENCRYPTED):
        return set()
    try:
        data = yaml.load(text, Loader=_Loader)  # noqa: S506 - a SafeLoader subclass
    except yaml.YAMLError:
        return set()
    return {str(k) for k in data} if isinstance(data, dict) else set()


def names_by_env(files: dict[str, str]) -> dict[str, set[str]]:
    """{environment: variable names} from {path: text}; paths outside the inventories are ignored."""
    out: dict[str, set[str]] = {}
    for path, text in files.items():
        match = VARS_FILE.match(path)
        if match:
            out.setdefault(match.group(1), set()).update(names_in(text))
    return out


def removed(base: dict[str, set[str]], now: dict[str, set[str]]) -> list[tuple[str, str]]:
    """(environment, name) for every variable the base had and the present does not."""
    return sorted((env, name) for env, names in base.items() for name in names - now.get(env, set()))


def readers(name: str, root: pathlib.Path) -> list[str]:
    """Files under roles/ and playbooks/ that name the variable as a whole word."""
    word = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")
    found = []
    for top in READ_BY:
        for path in sorted((root / top).rglob("*")):
            if not path.is_file() or path.suffix not in CODE:
                continue
            try:
                if word.search(path.read_text(encoding="utf-8", errors="ignore")):
                    found.append(str(path.relative_to(root)))
            except OSError:
                continue
    return found


def allowed(path: pathlib.Path = ALLOWED) -> dict[str, str]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)  # noqa: S603, S607


def base_rev() -> str | None:
    """The commit the change is compared with, or None when it cannot be told."""
    explicit = os.environ.get("INVENTORY_GUARD_BASE")
    candidates = [explicit] if explicit else (["HEAD^1"] if os.environ.get("GITHUB_ACTIONS") else [])
    for rev in candidates:
        if _git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}").returncode == 0:
            return rev
    for upstream in ("origin/main", "main"):
        merge_base = _git("merge-base", upstream, "HEAD")
        if merge_base.returncode == 0 and merge_base.stdout.strip():
            return merge_base.stdout.strip()
    return None


def files_at(rev: str) -> dict[str, str]:
    listing = _git("ls-tree", "-r", "--name-only", rev, "inventories/").stdout.splitlines()
    return {path: _git("show", f"{rev}:{path}").stdout for path in listing if VARS_FILE.match(path)}


def files_now(root: pathlib.Path = ROOT) -> dict[str, str]:
    out = {}
    for path in sorted((root / "inventories").rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and VARS_FILE.match(rel):
            out[rel] = path.read_text(encoding="utf-8", errors="ignore")
    return out


def check(base: dict[str, str], now: dict[str, str], root: pathlib.Path, accept: dict[str, str]) -> list[str]:
    """One line per variable removed while code still reads it."""
    problems = []
    for env, name in removed(names_by_env(base), names_by_env(now)):
        if name in accept:
            continue
        read_by = readers(name, root)
        if read_by:
            shown = ", ".join(read_by[:4]) + (f" (+{len(read_by) - 4} more)" if len(read_by) > 4 else "")
            problems.append(f"{name} (inventory {env}) is removed, and still read by {shown}")
    return problems


def main() -> int:
    rev = base_rev()
    if rev is None:
        if os.environ.get("GITHUB_ACTIONS"):
            print("inventory guard: no base commit to compare with (the checkout needs fetch-depth 2)")
            return 1
        print("inventory guard: no base commit to compare with (no origin/main) — skipped")
        return 0
    problems = check(files_at(rev), files_now(), ROOT, allowed())
    for line in problems:
        print(line)
    if problems:
        print(
            "\nAn inventory variable that code still reads must not disappear. Put it back, remove its"
            f"\nreaders in the same change, or list it with the reason in {ALLOWED.relative_to(ROOT)}."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
