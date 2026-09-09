# role: opnsense_token_rotation

SEC-09 schedule for the firewalls' Ansible API token. Runs **on the controller** (`hosts: localhost`, the
user that runs the playbooks): one systemd **user** timer per environment (`fw-token-rotation@<env>.timer`,
quarterly ≈ 90 d, `Persistent=true`) fires `fw-token-rotate.sh <env>`, which:

1. `ansible-playbook -i inventories/<env> playbooks/opnsense-api-bootstrap.yml -e opnsense_api_bootstrap_force_rotate=true`
   — mints a new key through the MVC, stores it in Vault `secret/<env>/opnsense/api`, deletes the old
   keys, and records `rotated_at` / `rotated_by` / `reason` in the secret's custom metadata;
2. gate: `ansible-playbook -i inventories/<env> playbooks/opnsense.yml --tags dns --check` must be
   `changed=0 failed=0` with the new token, else the unit fails (`systemctl --user --failed`).

Logs: `~/.local/state/fw-token-rotation/<env>-<stamp>.log`. Needs `loginctl enable-linger` for the
controller user (asserted). Prod's timer is installed **disabled** until its window (`opnsense_token_rotation_envs`).

```bash
ansible-playbook playbooks/opnsense-token-rotation.yml          # install / converge the timers
systemctl --user list-timers 'fw-token-rotation@*'              # next runs
systemctl --user start fw-token-rotation@test.service           # rotate now (test)
vault kv metadata get -mount=secret test/opnsense/api           # rotated_at / reason (on the Vault host)
```
