# roles/controller

The automation controller itself, managed like any other host.

| Concern | What the role does |
|---|---|
| Direct Vault path | A netplan drop-in routes `platform_internal_cidr4` through the firewall's OOB address, and `/etc/hosts` pins Vault's name, so `vault_login` reads Vault's API without the SSH hop. Before this, `playbooks/ssh-agent.yml` read the key passphrases from Vault **through the hop whose keys it was unlocking** — a circular bootstrap that left the platform unmanageable when the agent died (2026-09-22 23:13Z, recovered with the break-glass print kit). |
| Agent survives the session | `ssh-agent` runs as a lingering **user** service on the fixed socket instead of inside the desktop session. |

Firewall side: alias `host_controller` and rule `PASS OOB controller→SVC Vault API` in the prod catalog.

```bash
ansible-playbook -i inventories/prod/hosts.yml playbooks/controller.yml
```
