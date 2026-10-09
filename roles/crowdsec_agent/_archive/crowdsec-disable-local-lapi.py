#!/usr/bin/env python3
# Copyright (c) BY-SYSTEMS SRL
# SPDX-License-Identifier: MIT
# https://github.com/by-openclaw/ansible-platform
"""Remove the `api.server` block from a CrowdSec log processor's config.yaml.

A log processor must not run its own LAPI. If it does, `cscli lapi register`
is never reached and the agent quietly stays bound to 127.0.0.1 — it reports
"You can successfully interact with Local API", builds a private decision set,
and no bouncer ever reads it. That failure is invisible unless you check which
URL the credentials actually point at.

The CrowdSec multi-server guide says to remove the whole `api.server` section,
so that is exactly what this does: it deletes the `server:` key nested under
the top-level `api:` key and every line indented beneath it, leaving all other
lines — comments included — byte-identical.

Prints CHANGED or UNCHANGED. Idempotent: safe to run repeatedly.
"""
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "/etc/crowdsec/config.yaml"
src = open(path).read().splitlines(keepends=True)

out: list[str] = []
top: str | None = None
removed = False
i = 0

while i < len(src):
    line = src[i]
    text = line.rstrip("\n")

    # Track which top-level key we are inside (column-0, non-comment).
    if text and not text[0].isspace() and not text.startswith("#"):
        top = text.split(":", 1)[0].strip()

    indent = len(text) - len(text.lstrip())
    if top == "api" and indent == 2 and text.strip() == "server:":
        i += 1
        # Drop everything nested deeper than `server:`. A blank line is part of
        # the block; anything at column 0 (including a comment) ends it.
        while i < len(src):
            nxt = src[i].rstrip("\n")
            if nxt.strip() == "":
                i += 1
                continue
            if not nxt[0].isspace():
                break
            if (len(nxt) - len(nxt.lstrip())) <= 2:
                break
            i += 1
        removed = True
        continue

    out.append(line)
    i += 1

if removed:
    with open(path, "w") as fh:
        fh.write("".join(out))

print("CHANGED" if removed else "UNCHANGED")
