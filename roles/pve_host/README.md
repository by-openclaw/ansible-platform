# pve_host

The Proxmox VE hypervisor as code: from a bare Proxmox install to a platform node with one play
(`playbooks/pve-host.yml`). Apt sources (deb822, no-subscription), datacenter options, the Proxmox
firewall (IP sets from the inventory: management networks, admin desks, Traefik, bastion, monitoring;
default DROP; connectivity guard with automatic roll-back), the local admin `<org>@pam`, the OIDC realm
whose client `roles/authentik` mints into Vault, declared ACLs, and the UI route `proxmox.<domain>`
through Traefik. Exporters and agents come from their own plays (node group added to their targets);
hardening runs with `hardening_ufw_enabled: false` on nodes. Audit rows NODE-01…04.
