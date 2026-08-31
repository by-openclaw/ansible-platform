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
`contract_audit_service_checks` (per-group) in `defaults/main.yml`:

```yaml
- id: SEC-25a                 # ADR check ID from the checklist
  desc: "sshd listens on port 22222"
  probe: "sshd -T 2>/dev/null | awk '/^port /{print}'"  # shell run on the host
  expect: "port 22222"        # regex stdout MUST match (case-insensitive) to PASS
  groups: ["cluster"]         # optional; omitted/['all'] = every host, else SKIP
  absent: false               # optional; true = PASS when expect is NOT found
  delegate_localhost: true    # optional; run the probe on the controller (no sudo)
```

## Scope
Covers the machine-checkable **runtime** requirements. Non-automatable ADR
clauses (human judgment, external systems) stay in the checklist doc for manual
review. Static-code checks (pins, `:latest`, role greps) belong in CI lint, not
here. SEC-30 (step-ca CA distribution) returns in v2 once step-ca is deployed.
