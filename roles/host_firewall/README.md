# host_firewall

Generic "open my ports on ufw" step for service roles. A role sets `host_firewall_rules`
(port, proto, optional `from` list, comment) and includes this role at the end of its
tasks. Rules are expanded over every source network; when ufw is not installed the role
does nothing (the `hardening` baseline installs and enables ufw with SSH only).
Docker-published ports do not need rules (Docker's DNAT precedes the ufw INPUT chain);
native listeners do.
