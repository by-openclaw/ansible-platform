# ADR-0002: Full Replacement of sshd_config

**Status:** Accepted
**Date:** 2026-03-30
**Deciders:** @yboujraf

## Context

Patching `sshd_config` with lineinfile or blockinfile leads to configuration drift and zombie settings that accumulate over time. There is no reliable way to guarantee a known-good state when only patching individual directives.

## Decision

The hardening role **fully replaces** `sshd_config` from a managed template. No patching, no partial updates.

## Consequences

### Positive

- Every managed host has an identical, known-good SSH configuration.
- No zombie directives survive across role iterations.
- Auditing is trivial: diff the template against the deployed file.

### Negative

- A break-glass pattern is required: password auth is enabled for the break-glass group from OOB/MGMT networks only.
- Validation with `sshd -t` is mandatory before restarting the service to prevent lockouts.
- Any host-specific SSH customization must be modeled in the template variables, not applied out-of-band.

## Compliance

| Framework | Control | Relevance |
|---|---|---|
| ISO 27001 | A.13.1.1 | Network controls — full sshd config replacement ensures no undocumented access paths |
| ISO 27001 | A.12.6.1 | Management of technical vulnerabilities — template-driven config prevents configuration drift |
| NIS2 | Art.21(2)(c) | Physical and network security — enforced sshd policy across all managed hosts |
