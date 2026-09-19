# role: blackbox_exporter

Synthetic probes for the platform, on `lxc-monitoring-01` next to Prometheus (Debian package `prometheus-blackbox-exporter`, loopback `127.0.0.1:9115`). Born from incident #424: the resolver was down 12 h and nothing said so.

## Contract map

| Concern | How |
|---|---|
| Modules | `http_2xx` (follows redirects, TLS verified, 401/403 accepted for API-only or allow-listed routes), `dns_platform_v4` / `dns_platform_v6` (asks the resolver for `nextcloud.<domain>` and checks the split-DNS answer), `tcp_connect`, `tcp_tls` (also reports certificate expiry), `smtp_starttls` (EHLO → STARTTLS → certificate expiry of the mail ports), `icmp`. |
| Targets | Declared on the **prometheus** role (`prometheus_blackbox_*`); HTTPS targets are read from the live Traefik host list at play time, so a new route is probed as soon as it is published. |
| Exposure | loopback only; Prometheus scrapes `/probe`. No firewall or Traefik object. |
| Alerts | `platform-probes` rules in the prometheus role (ResolverDown 1 m, ProbeFailed 2 m, certificate 14 d / 5 d). |
| Version | Debian trixie package (0.26.x). |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/monitoring.yml
```

## Runbook

- `curl -s 'http://127.0.0.1:9115/probe?module=http_2xx&target=https://nextcloud.<domain>/status.php' | grep probe_success` on the host.
- A probe that fails only from the monitoring host usually means a firewall rule (SVC → DMZ is open by default; check the target's own host firewall) or a missing split-DNS override.
- ICMP runs unprivileged: the role sets `net.ipv4.ping_group_range = 0 65535` (an ambient `CAP_NET_RAW` is not honoured in the unprivileged LXC). If every ICMP probe fails, check that sysctl first.
- `mail.<domain>` is probed on `:8443` (split-DNS points straight at the mail server); `ca.` and `vpn.` are excluded from HTTPS (no internal record / WAN-only address) and covered by TCP probes on their daemons.
