# Contributing to ansible-platform

> Read [README.md](README.md) and [CLAUDE.md](CLAUDE.md) before starting.

---

## Before You Start

- Check existing issues and the [RAID.md](RAID.md) for known risks
- Open or link an issue before significant work
- For architecture-impacting changes, create or update an ADR in `docs/adr/`

---

## Setup

```bash
# Install collections
ansible-galaxy collection install -r requirements.yml

# Verify syntax
ansible-playbook playbooks/hardening.yml --syntax-check

# Dry-run (always first)
ansible-playbook playbooks/hardening.yml --check --diff
```

---

## Branch Naming

```text
{type}/{issue-id}-{short-description}
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `sec`

---

## Commit Standard

Conventional Commits — `type(scope): description`

```text
feat(hardening): add chrony NTP role
fix(sshd): correct match block for break-glass group
docs(readme): update role variable table
chore(ci): add ansible-lint workflow
```

| Type | Version bump | When |
|---|---|---|
| `fix:` | patch | Bug fixes |
| `feat:` | minor | New features |
| `feat!:` / `BREAKING CHANGE:` | major | Breaking changes |
| `docs:` `test:` `chore:` | none | Non-functional |

---

## Definition of Done — PR Checklist

- [ ] `ansible-playbook --syntax-check` passes
- [ ] `ansible-lint` passes (when configured)
- [ ] `--check --diff` runs clean on target hosts
- [ ] Idempotent: running twice produces no changes on second run
- [ ] Role variables documented in `defaults/main.yml` with comments
- [ ] README.md role table updated if variables changed
- [ ] CHANGELOG.md entry added
- [ ] CLAUDE.md current state updated if applicable

---

## Testing

### Dry-run (mandatory before any apply)

```bash
ansible-playbook playbooks/hardening.yml --check --diff
```

### Single host

```bash
ansible-playbook playbooks/hardening.yml -l srv-proxmox-poc-01 --check --diff
```

### Single tag

```bash
ansible-playbook playbooks/hardening.yml --tags ssh --check --diff
```

**Rule:** Never run without `--check` first unless explicitly instructed.

---

## Diagram Standard

- Source: PlantUML `.puml` → `assets/diagrams/`
- Render: PNG via Kroki → `assets/exports/`
- Docs link to `assets/exports/` only

---

## Post-Release Checklist

After each release:
- [ ] AGENTS.md — update Project Stats
- [ ] CLAUDE.md — update Current State if changed
- [ ] README.md — update version, role documentation

Commit: `docs: update project docs to v{version}`

---

## Release Process

- Use conventional commits consistently
- Release Please determines version bumps automatically
- Never manually edit version strings
