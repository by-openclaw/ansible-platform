#!/usr/bin/env bash
# Copyright (c) BY-SYSTEMS SRL
# SPDX-License-Identifier: Apache-2.0
# Source: https://github.com/by-openclaw/ansible-platform
#
# Image-pin guard: every container image this platform runs OR publishes must carry
# an explicit, immutable tag. A moving tag (`:latest`, `:stable`, `:main`, `:edge`)
# or no tag at all means a redeploy can silently change the running software.
# Run by pre-commit and by CI; exits non-zero with the offending lines.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
fail=0
report() { printf '  %s\n' "$1"; fail=1; }

# 1. moving tags anywhere in code (docs/comments may discuss them)
while IFS= read -r line; do
  [ -z "$line" ] && continue
  report "moving tag: $line"
done < <(grep -rnE ':(latest|stable|edge|main|master)([" ]|$)' \
           roles playbooks inventories 2>/dev/null \
         | grep -vE '\.md:' \
         | grep -vE '^\S+:[0-9]+:\s*#' \
         | grep -vE '#.*:(latest|stable|edge|main|master)' \
         | grep -vE 'stable-[0-9]' \
         | grep -vE '/archive/')

# 2. *_image variables without a tag (implicit :latest), skipping computed ones
while IFS= read -r v; do
  [ -z "$v" ] && continue
  report "untagged image variable: $v"
done < <(grep -rhnE '^[a-z0-9_]+_image: "[^"]+"' roles/*/defaults/main.yml 2>/dev/null \
         | grep -v '{{' | grep -v ':' )

[ "$fail" -eq 0 ] && echo "image pins: OK (every image carries an immutable tag)"
exit "$fail"
