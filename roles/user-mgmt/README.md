# role: user-mgmt

identity/0004 accounts: `svc-ansible-prod`, `svc-rune-prod`, `by-research` (break-glass) with keys via the rune agent; **purges foreign accounts** (`user_mgmt_purge_accounts`, guarded).

Play: `playbooks/user-mgmt.yml` / `identity-baseline.yml`.
