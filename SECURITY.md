# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ Current |
| < 0.1 | ❌ No fixes |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report privately via: security@by-systems.be

Include:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment (especially SSH lockout risk)
- Affected version(s) and target hosts

We aim to acknowledge reports within 48 hours and provide a fix within 14 days for confirmed issues.

## Scope

This repo manages SSH hardening, firewall rules, and fail2ban configuration. Security considerations:
- SSH port is 22222 (non-standard, hardened)
- Break-glass access via password auth is restricted to `break-glass` group from OOB/MGMT networks only
- sshd config is fully replaced (not patched) — any misconfiguration locks out all SSH access
- fail2ban bans are time-limited (default 3600s) but aggressive on repeated failures
