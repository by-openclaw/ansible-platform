# role: hardening

Debian baseline (security/0003): sshd 22222-only, fail2ban, sudo hygiene, kernel/module blacklists, AIDE, auditd (VMs), journald caps, core dumps restricted (CIS 1.5.1: pam_limits hard core 0, systemd DefaultLimitCORE=0, systemd-coredump Storage=none on VMs and the hypervisor — an LXC shares the host's core_pattern), apt-daily guard, Lynis gate ≥80 (per-host exception via `hardening_lynis_min_score`).

Play: `playbooks/hardening.yml` (FreeBSD FW excluded).
