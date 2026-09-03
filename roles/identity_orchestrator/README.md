# identity_orchestrator

The Entra-ID-like account fan-out. **Authentik is the front door** (define the
person + groups); this role reconciles a declarative people list into Authentik
(user + group memberships) and emails each person a confirmation bundle.

Human **mailboxes auto-provision** on first SSO login (the `mailcow-users` group
grants access) — this role does not create mailboxes; group membership drives it.

## People schema

```yaml
platform_people:
  - username: jdoe
    name: "Jane Doe"
    email: "jdoe@by-research.be"
    groups: ["nextcloud-users", "app-gitlab-dev", "mailcow-users"]
    state: active          # active | disabled  (disable, never delete)
```

Put the list in `inventories/prod/group_vars/all/people.yml` and run:

```
ansible-playbook -i inventories/prod playbooks/identity-provision.yml
```

## Boundaries

- Never emails a password — the confirmation carries the Authentik enrolment /
  recovery link only.
- Reconciles **to** Authentik (source of truth); never bypasses it.
- Removal = `state: disabled` (identity/0004 §1 — disable, never delete).

## Proven (canary 2026-09-03)

One test person → Authentik user created + added to `nextcloud-users` +
confirmation email delivered (recipient + adm delegate); canary then disabled.

## Follow-ups

- Vaultwarden collection/org membership per person (Vaultwarden API).
- Event-driven trigger (Authentik webhook) instead of the reconcile run.
