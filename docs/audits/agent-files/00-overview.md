# Audit: ansible-platform — Agent Files & Repo Health

> **Audited:** 2026-03-30
> **Auditor:** Rune (via Claude Opus)
> **Version:** v0.1.0 | **Commits:** 5 | **Files:** 29

---

## What exists

| File | Exists | Status |
|---|---|---|
| CLAUDE.md | Yes | Good — current state table, constraints, SSH port 22222 rule |
| AGENTS.md | Yes | Good — approval gates for prod changes, sub-agent background pattern |
| README.md | Yes | Good — quick start, role documentation, break-glass pattern |
| CONTRIBUTING.md | **No** | Missing |
| CHANGELOG.md | Yes | v0.1.0 only |
| SECURITY.md | **No** | Missing — SSH hardening repo should have one |
| RAID.md | **No** | Missing (references platform-setup issues) |
| docs/adr/ | Yes | Empty — README only, no decisions recorded |
| docs/audits/ | **No** | Created now |
| .github/ISSUE_TEMPLATE/ | **No** | Missing |
| .github/PULL_REQUEST_TEMPLATE.md | **No** | Missing |

---

## What's good

- CLAUDE.md has clear SSH port rule (22222) and constraint that check mode must work
- AGENTS.md has explicit approval gates (running without --check, adding hosts, SSH changes)
- README.md documents the hardening role components thoroughly
- Break-glass pattern is well-documented

---

## What's missing

| # | Item | Priority | Why |
|---|---|---|---|
| M1 | CONTRIBUTING.md | HIGH | No dev onboarding — how to run ansible-lint, test roles, submit changes |
| M2 | SECURITY.md | HIGH | This is a security hardening repo — it needs a vulnerability disclosure policy |
| M3 | RAID.md (per-repo) | MEDIUM | Repo-scoped risks (e.g., SSH lockout, fail2ban misconfiguration) |
| M4 | Repo-level ADRs | MEDIUM | No decisions recorded. Candidates: SSH port choice (22222), break-glass pattern, sshd full replacement strategy |
| M5 | Issue templates | LOW | No bug/feature templates |
| M6 | PR template | LOW | No PR checklist |
| M7 | `add-to-project` workflow | MEDIUM | Board automation missing (same as all repos) |
| M8 | Tests / molecule | LOW | No test infrastructure — deferred to post-lib-synology-dsm v1.0 |

---

## CLAUDE.md / AGENTS.md issues

| Item | Problem | Fix |
|---|---|---|
| CLAUDE.md references `doc-platform-core` RAID | Per-repo RAID decision pending | Update pointer once decided |
| AGENTS.md "Doc Maintenance" section | Should be in CONTRIBUTING.md (same finding as lib-synology-dsm) | Move when CONTRIBUTING.md created |
| AGENTS.md stats | 5 commits, 29 files — verify current | Update |
| No reference to refactor decisions or v1.0 timeline | This repo depends on lib-synology-dsm for Ansible collection | Add dependency note |

---

## Secrets check

- IP ranges (10.6.224.0/20, 10.6.240.0/20) in README — acceptable (private repo, needed for break-glass docs)
- No passwords, tokens, or SSH keys found in committed files

---

*Action: Create CONTRIBUTING.md, SECURITY.md. Record ADRs for SSH port and break-glass pattern. Add issue/PR templates from lib-synology-dsm as reference.*
