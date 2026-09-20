# host_firewall

Generic "open my ports on ufw" step for service roles. A role sets `host_firewall_rules`
(port, proto, optional `from` list, comment) and includes this role at the end of its
tasks. Rules are expanded over every source network. The role installs the ufw package and
stores the rules even while ufw is inactive, so enabling it later (the `hardening`
baseline: default deny + SSH + enable) never blocks a declared service.
Docker-published ports do not need rules (Docker's DNAT precedes the ufw INPUT chain);
native listeners do.
