# identity_orchestrator

The Entra-ID-like account fan-out. **Authentik is the front door** (define the
person + groups); this role reconciles a declarative people list into Authentik
(user + group memberships) and emails each person a confirmation bundle.

Human **mailboxes** are reconciled by this role through the mailcow API (Vault-native:
`prod/authentik/admin` token, `prod/mailcow/admin` API key, `prod/mailcow/s3` export key)
for every person holding the `mailcow-users` group:
- **joiner** — the mailbox exists *before* the first SSO login (`authsource: generic-oidc`,
  display name, quota 5 GB by default, aliases); the generated password is never used or stored.
- **mover** — name / quota / active / authsource reconciled only when they drift; aliases added idempotently.
- **leaver** (`state: disabled`) — login disallowed while mail is still accepted (mailcow `active=2`),
  optional forward + auto-reply as a prefilter sieve script (`sieve_filters`, what the UI writes),
  one-time export of the maildir to S3 `mailcow-backups/leavers/<user>-<date>.tar.gz`. Never deleted.
  Proven 2026-09-18 on a throwaway mailbox: Dovecot `sieve: redirect action: forwarded`, `vacation action: sent`,
  export object listed in S3, second run `changed=0`.

Per-person optional block: `mailbox: {quota_mb: 5120, aliases: [y.boujraf], forward_to: "x@…", leave_message: "…"}`.

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
