# RAID.md — ansible-platform

> Scope: repo-level risks, issues, and dependencies.
> Platform-wide items: doc-platform-core/docs/raid.md
> Rule: if it affects this repo only → here. If it crosses repos → platform RAID.

---

## Risks

| ID | Risk | Impact | Likelihood | Mitigation | Status |
|---|---|---|---|---|---|
| R-001 | sshd full replacement — misconfiguration locks out all SSH | CRITICAL | LOW | Validate with `sshd -t` before restart. Break-glass group on OOB/MGMT. | OPEN |
| R-002 | fail2ban aggressive bans on legitimate users | MEDIUM | LOW | Bantime 3600s (not permanent). Whitelist OOB/MGMT subnets. | OPEN |

| R-003 | No explicit `env` variable in group_vars per ADR-0010 — downstream tooling (Vault paths, NetBox tags) needs programmatic env label | MEDIUM | MEDIUM | Add `env: poc` to `inventories/poc/group_vars/all.yml` | OPEN |
| R-004 | CLAUDE.md/AGENTS.md did not reference ADR-0010/ADR-0012 | LOW | HIGH | Fixed in sprint Block 3 | IN PROGRESS |

## Issues

| ID | Issue | Priority | Status | GitHub |
|---|---|---|---|---|
| I-001 | No ansible-lint CI workflow | MEDIUM | OPEN | — |
| I-002 | No molecule test infrastructure | LOW | OPEN | Deferred post-lib-synology-dsm v1.0 |

## Dependencies

| ID | Dependency | Blocks | Status |
|---|---|---|---|
| D-001 | Target hosts must have SSH on port 22222 | All playbook runs | OK — hardening role sets this |
| D-002 | Vault deployment (Phase 2) | Users role (secret injection) | BLOCKED |
