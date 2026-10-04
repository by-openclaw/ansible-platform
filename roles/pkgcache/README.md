# role: pkgcache

The package caches of the platform on `lxc-pkgcache-01`: **devpi** (caching mirror of PyPI, `pypi.<domain>`, private route) and **apt-cacher-ng** (caching proxy for Debian repositories, port 3142). Both images are built on the guest from a pinned official base and a pinned package version (`defaults/main.yml`).

- **devpi**: `devpi-server` (no web/search plugin: its index of all of PyPI kept the guest busy for hours), server directory `/var/lib/devpi` (created once by `devpi-init`), only `root` may modify (`--restrict-modify root`; credential in Vault `{env}/pkgcache/devpi-root`). Clients: `https://pypi.<domain>/root/pypi/+simple/`.
- **apt-cacher-ng**: the Debian package, settings passed as arguments (the package's repository mappings stay as shipped), cache in `/var/cache/apt-cacher-ng`. Clients: `Acquire::http::Proxy "http://lxc-pkgcache-01.<domain>:3142";`.
- Both containers run on a read-only root filesystem, without capabilities, as their own account.
- **Upgrade**: bump a pin and the revision → the play rebuilds and recreates.

Run: `ansible-playbook -i inventories/prod playbooks/pkgcache.yml`.

## Backup & restore

Class **E**: caches only, refilled from upstream. Restore = run the play. Full matrix: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `GET /+api` on 3141 answers 200; `GET /acng-report.html` on 3142 answers 200. The play also fetches a PyPI project index and a Debian index through each cache.
- A cache that cannot reach upstream serves what it already holds and fails on the rest: check the guest's outbound access first.
- Disk: both caches only grow; apt-cacher-ng expires what upstream dropped (its daily job), devpi keeps what was fetched. The guest's disk alert (`HostDiskAlmostFull`) is the signal.
