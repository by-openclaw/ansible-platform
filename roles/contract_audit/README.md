# role: contract_audit

Idempotent, **read-only** compliance audit of each host/service against the ADR
contract (`docs/audits/adr-compliance-checklist.md`). It runs probes and scores
each check `PASS` / `FAIL` / `SKIP` per ADR check ID. It **changes nothing** —
every task is `changed_when: false`, so it is idempotent by construction.

## Run
```bash
# Report-only scorecard (per-host PASS/FAIL/SKIP + failing IDs)
ansible-playbook -i inventories/prod/hosts.yml playbooks/contract-audit.yml

# As a CI/pre-merge gate — fails the play on ANY FAIL
ansible-playbook -i inventories/prod/hosts.yml playbooks/contract-audit.yml -e contract_audit_enforce=true
```

## Add a check (data-driven)
Append a row to `contract_audit_checks` (host-wide) or
`contract_audit_service_checks` (per-group) in `defaults/main.yml`. A check is a list of
**probes**; each probe reads one thing on the host — no shell, no pipe — and states what
that text must say. Every probe of a check must hold.

```yaml
- id: SEC-25a                 # ADR check ID from the checklist
  desc: "sshd listens on the baseline port"
  groups: ["cluster"]         # optional; omitted/['all'] = every host, else SKIP
  probes:
    - argv: [sshd, -T]        # a command (a list): its standard output is the text
      expect: "^port {{ platform_ssh_port }}$"   # regex that must be found
```

| What a probe reads | Key | The text is |
| --- | --- | --- |
| a command | `argv: [..]` | its standard output |
| an HTTP GET from the host | `url:` (+ `read: content`, `validate_certs: false`, `timeout:`) | the status code, or the body with `read: content`; redirects are not followed |
| a file | `file:` | its content (`''` when it does not exist) |
| a value Ansible holds | `value:` | that value |

| What the text must say | Key |
| --- | --- |
| a regex, or each regex of a list, is found | `expect:` |
| a regex, or any regex of a list, is NOT found | `forbid:` |
| the number captured is at least a minimum | `capture:` + `min:` |
| a regex matches exactly N times | `count:` + `equals:` |

Regexes are case-insensitive and `^` / `$` match at each line. A probe that cannot run (no
such command, no such file, no answer) reads as `''`: the check fails on its own terms.
`sensitive: true` on a probe whose text carries secrets (a container's `DATABASE_URL`, a
configuration file): its result is never logged.

## Scope
Covers the machine-checkable **runtime** requirements. Non-automatable ADR
clauses (human judgment, external systems) stay in the checklist doc for manual
review. Static-code checks (pins, `:latest`, role greps) belong in CI lint, not
here. SEC-30 (step-ca CA distribution) returns in v2 once step-ca is deployed.
