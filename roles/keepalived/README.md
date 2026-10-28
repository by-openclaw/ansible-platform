# Role: keepalived

One address for several instances of a service: VRRP (RFC 5798) as implemented by keepalived.
The address belongs to the instance with the highest priority whose health script passes; when
that instance stops answering, the next one owns the address within the advertisement interval
(1 s), and the preferred instance takes it back when it is healthy again (preemption is
keepalived's default).

First consumer: the platform resolver (ADR infra/0011) — two AdGuard Home instances, the virtual
address `platform_resolver_vip4/6` is what every guest, DHCP lease and router advertisement names.

## What the role does

| Step | Vendor reference |
|---|---|
| `keepalived` package, `/etc/keepalived/keepalived.conf` rendered from `keepalived_instances` and `keepalived_scripts`, validated with `keepalived --config-test` | keepalived.conf(5): `vrrp_instance`, `vrrp_script`, `track_script`, `unicast_peer`, `native_ipv6` |
| ufw admits IP protocol 112 from each peer (`proto vrrp`), through roles/host_firewall | ufw(8) |
| daemon enabled, configuration reloaded (SIGHUP) on change | keepalived(8) |

## Declaring an address (inventory group_vars of the consumer)

```yaml
keepalived_scripts:
  - {name: svc_answers, command: "/usr/bin/<probe> …", interval: 2, timeout: 3, fall: 2, rise: 2, weight: -60}
keepalived_instances:
  - name: svc_v4
    family: 4
    interface: "{{ ansible_facts['default_ipv4']['interface'] }}"
    virtual_router_id: 53            # unique per link and family
    priority: "{{ 150 if inventory_hostname == (groups['svc'] | first) else 100 }}"
    unicast_src: "{{ ansible_host }}"
    unicast_peers: "{{ groups['svc'] | difference([inventory_hostname]) | map('extract', hostvars, 'ansible_host') | list }}"
    virtual_ips: ["10.1.3.100/24"]
    track_script: svc_answers
```

`weight -60` on the script: a failing probe lowers the owner (150) below the peer (100) — the
address moves; the probe passing again restores the priority and the address returns.

## Acceptance test (ADR infra/0011 §4)

Stop the service on the owner: lookups through the virtual address keep answering (< 100 ms from a
host and from a container); then stop keepalived on the owner; then start both and confirm the
address is back on the preferred instance.

## Controls

ISO 27001:2022 A.8.14 (redundancy of information processing facilities), A.8.9 (configuration
management: the address is declared once, in the inventory).
