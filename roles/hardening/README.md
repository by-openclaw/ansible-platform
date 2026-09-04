# role: hardening

Debian baseline (security/0003): sshd 22222-only, fail2ban, sudo hygiene, kernel/module blacklists, AIDE, auditd (VMs), journald caps, apt-daily guard, Lynis gate ≥80 (per-host exception via `hardening_lynis_min_score`).

Play: `playbooks/hardening.yml` (FreeBSD FW excluded).
