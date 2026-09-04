# role: mailbox

Per-service rx/tx mailbox (`{svc}@`) via the mailcow API: Vault creds `{env}/mail/{svc}`, aliases, **delegates** (adm co-delivery + send-as, declarative reconcile), plus-addressing free. `mailbox_state: absent` deactivates (archive-before-destroy).

Fan-out list: `playbooks/mailboxes.yml`.
