# AGENTS.md — ansible-platform

## Sub-agent rules

- Long Ansible runs (>30s) → use background pattern from ADR-0006 §7
- Write progress to `workspace/state/ansible-{play}-{host}.json`
- Never run `ansible-playbook` without `--check` first unless explicitly instructed
- Never modify inventory hosts without human approval
- Never store secrets in playbooks, vars files, or templates

## What agents may do freely

- Add/update roles, tasks, templates, handlers
- Update group_vars / host_vars (no secrets)
- Add new playbooks following the existing pattern
- Update README, CLAUDE.md, AGENTS.md
- Run in check mode

## What requires explicit approval

- Running playbooks without `--check` (actual changes to prod/poc hosts)
- Adding new hosts to inventory
- Changing SSH port or authentication config
- Any change that could lock out SSH access

## Commit convention

`feat|fix|docs|chore|refactor(scope): subject`

Scope = role name or component: `hardening`, `users`, `vault`, `inventory`

## Doc Maintenance — After Every Successful Build

After each successful CI build (all jobs green), update these files to reflect current state:
- **AGENTS.md** — Update "Project Stats", version, checklist, roadmap progress
- **CLAUDE.md** — Update build commands, file table, current state if anything changed
- **README.md** — Update badges, feature lists, version numbers

Commit separately: `docs: update project docs to v{version}`

This ensures any AI agent (or human) picking up the project always has accurate, current documentation.

---

## Project Stats

> Auto-updated on every release. Last updated: 2026-03-29

| Metric | Value |
|---|---|
| Version | v0.1.0 |
| Tagged releases | 1 |
| Total commits | 5 |
| Total files | 29 |
| Python source files | 0 |
| Test files | 0 |
| Terraform files | 0 |
| YAML/Ansible files | 15 |
| ADR decisions | 0 |
| CI workflows | 1 |

