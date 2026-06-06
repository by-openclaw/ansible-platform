#!/usr/bin/env bash
# fw_drift_check.sh — FW reproducibility / drift gate (ansible MVC side).
#
# Runs the declarative catalog against the live FW in DRY-RUN (--check) and FAILS
# if the device differs from the catalog (any pending change) or any section
# errors. This is what makes config drift FAIL LOUDLY instead of being discovered
# by hand later (issue #35).
#
# It is an OPERATOR gate (needs live FW API reachability + the env secret), not a
# CI gate — run it after every apply and before declaring the FW "clean".
# The terraform side of reproducibility is covered separately in
# infra-terraform-proxmox (`terraform plan` must show 0 drift; see that repo #27).
#
# Usage:
#   scripts/fw_drift_check.sh [--env prod] [--only fw|dns|kea|dnsmasq|radvd] \
#                             [--secret-file PATH]
# Exit codes: 0 = clean (0 changes, 0 errors) · 1 = drift or errors · 2 = run error
#
# Copyright BY-SYSTEMS SRL — SPDX-License-Identifier: MIT
# https://github.com/by-openclaw/ansible-platform
set -euo pipefail

ENV="prod"
PASSTHRU=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env) ENV="$2"; PASSTHRU+=(--env "$2"); shift 2 ;;
    --only|--secret-file) PASSTHRU+=("$1" "$2"); shift 2 ;;
    *) PASSTHRU+=("$1"); shift ;;
  esac
done
# Ensure --env is passed to the python tool exactly once.
case " ${PASSTHRU[*]} " in *" --env "*) : ;; *) PASSTHRU+=(--env "$ENV") ;; esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"

echo "▶ FW drift gate — env=${ENV} — dry-run check against live FW…"
OUT="$("$PY" "${SCRIPT_DIR}/fw_apply_direct.py" --check "${PASSTHRU[@]}" 2>&1)" || {
  echo "$OUT"
  echo "✗ drift gate: fw_apply_direct.py failed to run (connectivity/creds?)." >&2
  exit 2
}
echo "$OUT"

# Parse the summary line: "Total: N  Errors: E  Changes: C"
SUMMARY="$(grep -E '^Total: [0-9]+ +Errors: [0-9]+ +Changes: [0-9]+' <<<"$OUT" | tail -1 || true)"
if [[ -z "$SUMMARY" ]]; then
  echo "✗ drift gate: could not find summary line in output." >&2
  exit 2
fi
ERRORS="$(sed -E 's/.*Errors: ([0-9]+).*/\1/' <<<"$SUMMARY")"
CHANGES="$(sed -E 's/.*Changes: ([0-9]+).*/\1/' <<<"$SUMMARY")"

echo "──────────────────────────────────────────────"
if [[ "$ERRORS" -eq 0 && "$CHANGES" -eq 0 ]]; then
  echo "✓ FW is reproducible: 0 changes, 0 errors — live == catalog."
  exit 0
fi
echo "✗ DRIFT DETECTED: ${CHANGES} change(s), ${ERRORS} error(s) — live ≠ catalog."
echo "  Reconcile via: apply the catalog (drop --check) OR update the catalog to match intent."
exit 1
