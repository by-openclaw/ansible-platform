## Summary

<!-- What changed and why. One sentence. -->

Closes #___

## Type

- [ ] Feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Chore / refactor
- [ ] Security

## Verification

<!-- Check what applies to THIS change. Not all boxes apply to every PR. -->

### Code quality (if code changed)
- [ ] Linting clean (ruff / ansible-lint / terraform fmt)
- [ ] Type checking clean (mypy — if applicable)
- [ ] Unit tests pass
- [ ] Integration tests pass (if touching live infra/NAS)
- [ ] Coverage maintained (no drop)

### Security (always)
- [ ] No secrets, tokens, or passwords in committed files
- [ ] No `<REDACTED>` values in code (only in docs)
- [ ] ADR compliance section present (if new ADR)

### Documentation (if applicable)
- [ ] CHANGELOG entry added
- [ ] CLAUDE.md updated (if state changed)
- [ ] RAID.md updated (if new risk/issue found)

### Idempotency (if automation/lib code)
- [ ] ensure() returns EnsureResult with correct action
- [ ] dry_run=True tested
- [ ] Running twice produces same result

## Review

- [ ] @by-opus review requested (label: `review:opus`)

