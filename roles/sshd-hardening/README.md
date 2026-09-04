# role: sshd-hardening

Full `sshd_config` template — port 22222 only, key-only, root disabled (PVE break-glass carve-out). Validates with `sshd -t` before restart.

Part of `identity-baseline.yml`.
