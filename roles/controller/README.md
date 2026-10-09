# roles/controller

The automation controller itself, managed like any other host.

| Concern | What the role does |
|---|---|
| Direct Vault path | A netplan drop-in routes `platform_internal_cidr4` through the firewall's OOB address, and `/etc/hosts` pins Vault's name, so `vault_login` reads Vault's API without the SSH hop. Before this, `playbooks/ssh-agent.yml` read the key passphrases from Vault **through the hop whose keys it was unlocking** — a circular bootstrap that left the platform unmanageable when the agent died (2026-09-22 23:13Z, recovered with the break-glass print kit). This part is applied only where sudo asks for no password; elsewhere the play reports it and Vault stays reachable through the SSH hop (`-K` does not help: the inventory's `ansible_become_password` wins over it). |
| Agent survives the session | `ssh-agent` runs as a lingering **user** service on the fixed socket instead of inside the desktop session. |
| HashiCorp repository and Terraform | The repository's signing key is pinned by fingerprint (`controller_hashicorp_key_fingerprint`): downloaded as the user, compared, then installed for apt; the source is a deb822 file; Terraform is installed at `controller_terraform_version` and held. Needs root, through the automation account (row below). A new HashiCorp key = a reviewed change of the pinned fingerprint. |
| Automation account | `identity/0004-os-accounts §4`: automation escalates as `svc-ansible-{env}` with the password Vault holds; a person's password is typed, never stored. `tasks/automation_account.yml` creates that account on the controller once — `ansible-playbook playbooks/controller.yml --tags account`, the person types their own sudo password at the prompt — with the fleet's own account task (`roles/user-mgmt`): Vault password, sudoers with a password, the automation key accepted from the controller itself only, and an sshd rule that refuses a password login for it. From then on the role's root work connects to the controller over SSH as that account and needs no person; each run first proves that path (`id -u` = 0). |

Firewall side: alias `host_controller` and rule `PASS OOB controller→SVC Vault API` in the prod catalog.

```bash
ansible-playbook -i inventories/prod/hosts.yml playbooks/controller.yml
```
