# Package caches — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: pkgcache`). Role `roles/pkgcache`, play `playbooks/pkgcache.yml`, guest `lxc-pkgcache-01` (ct 519). Two containers: `devpi` (caching mirror of PyPI, `pypi.<domain>` behind the edge) and `apt-cacher-ng` (caching proxy for Debian package repositories, port 3142).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** none of the identity ADRs applies to a human here — the caches are read by machines (pip, apt cannot follow an SSO flow). `sso: none` in the catalog, like the data endpoint.
2. **Authentik application:** none.
3. **Access model:** reading is open to whoever reaches the service — the PyPI cache through the edge's private route (LAN and VPN only), the Debian proxy from the platform's networks (`group_vars/all/docker_firewall.yml`: `trusted`). Writing is closed: devpi runs with `--restrict-modify root` (only its `root` user may create users or indexes) and no private index exists; the proxy has no write interface.
4. **Vault paths:** `secret/{env}/pkgcache/devpi-root` (devpi's `root` user, get-or-create).
5. **Ansible adapter + vars:** `roles/pkgcache` (`defaults/main.yml`: the base image and package pins, ports, directories, the URLs clients configure; `templates/Dockerfile.*.j2` build the two platform images on the guest; `service_scaffold` runs the containers and the edge route).
6. **Removal notes:** `playbooks/decommission-service.yml`; class E — nothing to archive, the caches refill from upstream.

## Notifications (services/0005)

1. **Transport:** none — the caches send no mail (`mailbox: false`).
2. **What is sent:** nothing.
3. **Alerting path:** Prometheus — blackbox `https://pypi.<domain>/` + `node` + `cadvisor` → Alertmanager → Discord/mail (platform).
4. **Logs:** container stdout → journald → promtail → Loki (`container="devpi"`, `container="apt-cacher-ng"`); the proxy's transfer log in `/var/log/apt-cacher-ng` (rotated, 14 days).
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class E (`docs/backup.md`): cached files only. The guest is in the PBS and NAS jobs; rebuild = the play (the caches refill on first use).

## Use

- **pip / uv / poetry:** index `https://pypi.<domain>/root/pypi/+simple/` (`pkgcache_pypi_index_url`). GitLab CI gets it as the instance variable `PIP_INDEX_URL`.
- **apt:** `Acquire::http::Proxy "http://lxc-pkgcache-01.<domain>:3142";` (`pkgcache_apt_proxy_url`) on a host of the platform's networks. HTTPS repositories are tunnelled, not cached.
- **Upgrade:** bump a pin (`pkgcache_devpi_server_version`, `pkgcache_acng_version`, a base image) and the matching revision; the play rebuilds the image and recreates the container.
