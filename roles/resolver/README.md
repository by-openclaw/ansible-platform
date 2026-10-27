# Role: resolver

Every guest resolves through AdGuard, and keeps honouring router advertisements even where
something turned IPv6 forwarding on.

## Why

Nothing set the resolver on guests at all. Surveyed on 2026-09-09, **every** guest pointed
straight at the firewall's Unbound:

```
lxc-harbor-01 / lxc-gitlab-01 / lxc-monitoring-01
  nameserver 10.1.3.1        nameserver fd01:3::1
```

Those queries still resolve, and still reach an encrypted upstream through dnscrypt-proxy —
but they are neither filtered nor visible in AdGuard. AdGuard is where DNS policy and query
visibility live, so a guest that skips it is outside both.

## What it does

| | |
|---|---|
| Resolvers | AdGuard v4, then the firewall's Unbound, then AdGuard v6 — `options timeout:1 attempts:2` |
| Where | `systemd-resolved` drop-in when it is running, `/etc/resolv.conf` otherwise |
| RA handling | `accept_ra=2` on hosts where forwarding silently disabled it |

## Two things worth knowing

**The fallback is deliberate.** AdGuard is a single VM. Without a fallback its reboot takes
name resolution down platform-wide — including Vault and Traefik — which is worse than
briefly resolving unfiltered. The resolver library only reaches the fallback when AdGuard
does not answer — and only after its timeout. The order and the options are the point: the
firewall is the SECOND entry and a server gets 1 s x 2 attempts, so a dead AdGuard costs about
2 s per lookup. With the defaults (5 s x 2, firewall third) it cost 20 s, every client gave up
first, and on 2026-10-24 one full resolver disk took the platform down for three days with the
fallback sitting unused in every resolv.conf.

**`/etc/resolv.conf` honours at most three nameservers.** glibc's `MAXNS` is 3 and silently
ignores the rest, so the file gets AdGuard v4, the firewall v4 and AdGuard v6, in that order.
`systemd-resolved` has no such limit and receives the full list.

## The RA fix, precisely

Linux reads `accept_ra=1` as *"accept router advertisements only while forwarding is off"*.
Docker turns on IPv6 forwarding for its bridge, so a Docker host silently stops processing
RAs: no SLAAC address, and no future RA — resolver, MTU, prefix, route — ever reaches it.

The role changes this **only** where it was silently disabled: interface `accept_ra=1` **and**
`forwarding=1`. A host with `accept_ra=0` has deliberately opted out (AdGuard does, with a
static IPv6 route) and is left alone. The check reads the interface's own sysctls, not `all`
— the kernel uses the per-interface value, and reading `all` wrongly flagged a host whose
interface was set to ignore RAs.

## Run

```bash
ansible-playbook -i inventories/prod playbooks/hardening.yml --tags resolver --check --diff
ansible-playbook -i inventories/prod playbooks/hardening.yml --tags resolver
```

Applied to every guest as part of the hardening baseline, so provisioning a new guest sets it.

## Follow-up

A Proxmox container's `/etc/resolv.conf` is seeded from the CT config at creation, so the same
values belong in the Terraform guest definition. This role owns the running state.
