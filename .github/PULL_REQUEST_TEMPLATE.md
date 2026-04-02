## Summary

<!-- One sentence: what changed and why. -->

## Issue

<!-- REQUIRED: Link the issue this PR addresses. -->
Closes #

## Type

<!-- Select ONE. -->
- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] chore — maintenance, refactor, CI
- [ ] security — security fix or hardening

## Changes

<!-- Bullet list of what was done. Keep it short. -->
-
-

## Checklist

<!-- Check what applies. Not all boxes apply to every PR. -->

### Quality
- [ ] Lint clean (`ruff` / `ansible-lint` / `terraform fmt`)
- [ ] Tests pass (`pytest` / `terraform plan`)
- [ ] No coverage drop

### Security
- [ ] No secrets, tokens, or passwords in committed files
- [ ] No `<REDACTED>` in code (docs only)

### Docs
- [ ] CHANGELOG entry added (if user-facing change)
- [ ] CLAUDE.md updated (if repo state changed)

## Review

- [ ] Label `review:opus` added
- [ ] Opus reviewed and approved (label: `opus:approved`)
- [ ] @yboujraf approved

<!--
Merge rules (ADR-0019):
- Agents open PRs, never merge
- @yboujraf is sole merge authority
- No force-push to main — ever
-->
