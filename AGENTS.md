# AGENTS.md -- ansible-platform


Ansible playbooks and roles for BY-SYSTEMS platform -- OS hardening, service deployment, user provisioning.

## Sub-agent rules

- Long Ansible runs (>30s) -- use background pattern from ADR-0006 S7
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

## Coding & Commit Standards

- **Scope** = role name or component: `hardening`, `users`, `vault`, `inventory`
- **Linting:** `ansible-lint` -- must be clean before commit
- **Branch naming:** `feat/{issue-id}-{description}` or `fix/{issue-id}-{description}`

---

## Project Stats

> Auto-updated on every release. Last updated: 2026-03-31

| Metric | Value |
|---|---|
| Version | v0.1.1 |
| Tagged releases | 2 |
| Total files | 43 |
| Python source files | 0 |
| Test files | 0 |
| Terraform files | 0 |
| YAML/Ansible files | 14 |
| ADR decisions | 2 |
| CI workflows | 1 |
