#!/usr/bin/env python3
# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/ansible-platform
"""pre-commit + CI: every container image this platform runs OR publishes must carry an explicit,
immutable tag. A moving tag (`:latest`, `:stable`, `:edge`, `:main`, `:master`) or no tag at all
means a redeploy can silently change the running software.

A line under roles/, playbooks/ or inventories/ fails when one of those tags is followed by a
quote, a space or the end of the line. Prose may name them, so these are not code: Markdown, a
comment line, a `#` written before the tag, a `stable-<digit>` release name, an `/archive/` path.
Exit 1 lists every offending `path:line:text`; exit 0 prints the OK line.

Replaces scripts/check_image_pins.sh (the repo keeps no .sh) and gives the same result. Files
are read the way that script's `grep -r` read them in a UTF-8 locale: every file on disk,
tracked or not; a symlink inside the trees is not followed; a binary file (NUL byte) is skipped;
lines are split on LF only; a line that is not valid UTF-8 is skipped. The `grep -v` filters run
on grep's whole `path:line:text` record, as the pipeline did, not on the text alone.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
from collections.abc import Iterator

ROOTS = ("roles", "playbooks", "inventories")
OK = "image pins: OK (every image carries an immutable tag)"

MOVING_TAG = re.compile(r':(latest|stable|edge|main|master)([" ]|$)')

# grep's \s in a UTF-8 locale is glibc's isspace. Python's \s also takes NBSP, U+2007, U+202F,
# U+0085 and U+001C-U+001F, so the class is spelled out: a comment is recognised as grep did.
_WS = r"\t\n\v\f\r \u1680\u2000-\u2006\u2008-\u200a\u2028\u2029\u205f\u3000"

NOT_CODE = (
    re.compile(r"\.md:"),                                  # Markdown
    re.compile(rf"^[^{_WS}]+:[0-9]+:[{_WS}]*#"),           # a comment line
    re.compile(r"#.*:(latest|stable|edge|main|master)"),   # a comment before the tag
    re.compile(r"stable-[0-9]"),                           # stable-NNNN is a release name, a pin
    re.compile(r"/archive/"),                              # archived, not deployed
)

IMAGE_VAR = re.compile(r'^[a-z0-9_]+_image: "[^"]+"')


def _files(top: str) -> Iterator[str]:
    """Regular files under top in `grep -r` order: directory order, depth first. A symlink met
    inside the tree is not followed; a missing or unreadable directory is skipped."""
    try:
        with os.scandir(top) as it:
            entries = list(it)
    except OSError:
        return
    for entry in entries:
        if entry.is_dir(follow_symlinks=False):
            yield from _files(entry.path)
        elif entry.is_file(follow_symlinks=False):
            yield entry.path


def _lines(path: str) -> Iterator[tuple[int, str]]:
    """(line number, text) as grep sees them: split on LF only (a CR stays in the text),
    nothing from a binary file, no line that is not valid UTF-8."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return
    if b"\0" in data:
        return
    lines = data.split(b"\n")
    if lines[-1] == b"":  # the LF ending the last line starts no new one
        lines.pop()
    for number, raw in enumerate(lines, 1):
        try:
            yield number, raw.decode("utf-8")
        except UnicodeDecodeError:
            continue


def moving_tags() -> list[str]:
    """Every `path:line:text` record with a moving tag in code, in the order grep printed them."""
    found = []
    for root in ROOTS:
        for path in _files(root):
            for number, text in _lines(path):
                if MOVING_TAG.search(text):
                    record = f"{path}:{number}:{text}"
                    if not any(rx.search(record) for rx in NOT_CODE):
                        found.append(record)
    return found


def untagged_image_vars() -> list[str]:
    """`*_image` defaults without a tag (an implicit :latest), computed ones skipped.

    Ported as the .sh had it, and as there it never reports: its filters read grep's `N:text`
    record, which always contains ':'. Testing the value's own tag instead is a rule change, not a
    port: today it would flag verdaccio_platform_image, a repository name that roles/verdaccio
    tags where it uses it."""
    found = []
    for path in sorted(glob.glob("roles/*/defaults/main.yml")):
        for number, text in _lines(path):
            record = f"{number}:{text}"
            if IMAGE_VAR.search(text) and "{{" not in record and ":" not in record:
                found.append(record)
    return found


def main() -> int:
    # The .sh ran `cd "$(git rev-parse --show-toplevel)"`: outside a repo it stayed where it was.
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], stdout=subprocess.PIPE, text=True, check=False
        ).stdout.rstrip("\n")
    except OSError:
        top = ""
    if top:
        os.chdir(top)

    bad = [f"moving tag: {record}" for record in moving_tags()]
    bad += [f"untagged image variable: {record}" for record in untagged_image_vars()]
    for line in bad:
        print(f"  {line}")
    if not bad:
        print(OK)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
