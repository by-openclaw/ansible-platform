# role: hardening

Debian baseline (security/0003): sshd 22222-only, fail2ban, sudo hygiene, kernel/module blacklists, AIDE, auditd (VMs), journald caps, core dumps restricted (CIS 1.5.1: pam_limits hard core 0, systemd DefaultLimitCORE=0, systemd-coredump Storage=none on VMs and the hypervisor — an LXC shares the host's core_pattern), apt-daily guard, Lynis gate ≥80 (per-host exception via `hardening_lynis_min_score`).

Play: `playbooks/hardening.yml` (FreeBSD FW excluded).

journald: disk caps plus `RuntimeMaxUse` for the volatile journal under /run (journald.conf(5): the default
is 10 % of the tmpfs capped at 4 GB — the host's RAM as seen from an LXC), and the journal is flushed back
to /var/log/journal whenever journald fell back to volatile mode (journalctl(1) `--flush`, idempotent).
ISO 27001:2022 A.8.15 logging, A.8.6 capacity management.

Swap (VMs, `tasks/swap.yml`): a swap file sized by the Red Hat Enterprise Linux 9 table (RAM < 2 GiB → 2 × RAM; 2–8 GB → equal to RAM; 8–64 GB → 4 GB), overridden per host where the product documents its own requirement (mailcow 1 GiB; GitLab, Kubernetes and Vault: none). Containers get their swap allowance from the node (Terraform, pct(1) default 512 MB); nodes keep the installer's swap volume. ISO 27001:2022 A.8.6 capacity management.
