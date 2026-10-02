# Hardening overrides — processes that run as root

`security/0003-hardening` §1: every container process runs as a non-root UID; an exception needs
explicit written approval, documented here, reviewed annually. This file is the register. An
entry is valid only with an approval line; a missing or expired approval = the exception is void
and the service is non-compliant.

| # | Service / container | Hosts | Why root is required | Containment | Approval | Review by |
|---|---|---|---|---|---|---|
| OH-1 | `cadvisor` (`roles/cadvisor`) — container metrics agent | every Docker host | Reads the kernel's cgroup/namespace accounting of *other* containers: `/sys/fs/cgroup`, `/var/lib/docker` (overlay metadata), `/dev/disk`; a non-root UID cannot read other containers' cgroup files. Upstream ships and documents the image root-only. | `privileged: false`; every host mount **read-only** (`/`, `/var/run`, `/sys`, `/var/lib/docker`, `/dev/disk`); no capabilities added; `--docker_only`; listens on the SVC address only, ufw admits the Prometheus scrapers only; pinned image. | **pending — @yboujraf** | 2027-10-01 |
| OH-2 | `portainer-agent` (`roles/portainer`) — console agent | every Docker host | Talks to the Docker daemon through `/var/run/docker.sock` and browses `/var/lib/docker/volumes`; the socket is root-owned and the Docker API is root-equivalent by design — a non-root UID in the container changes nothing about what the socket grants. | Reachable from the Portainer console host only (ufw + `AGENT_SECRET`); the console itself is behind Traefik + Authentik SSO (`portainer-admins`); pinned image; journald logging. Removing the agent = losing the fleet console. | **pending — @yboujraf** | 2027-10-01 |
| OH-3 | `nextcloud` + `nextcloud-cron` (`roles/nextcloud`, image `nextcloud:34.0.4-apache`) — vendor entrypoint | `lxc-nextcloud-01` | The upstream image's entrypoint starts as root to prepare `/var/www/html` and the data directory, then Apache's master (PID 1) stays root while **every request is served by `www-data` workers** (10 workers observed, uid 33); the cron container runs the same image. Upstream ships no rootless variant of the Apache image. | Image pinned (upgrade_path for majors); `privileged: false`; the only root process is Apache's master; workers, cron jobs and the metrics sidecar are non-root; published port reachable from Traefik only; read-only rootfs + tmpfs pending the platform pass. Replace with a rootless upstream variant when one exists. Proposed ADR clause: doc-platform-core #68 (§1). | **pending — @yboujraf** | 2027-10-01 |

Not an exception: `node_exporter` runs as a native service user; service containers that run with
their own non-root UID (Authentik, GitLab, …) need no entry — a service that *serves requests* as
root is a finding, not an entry here. A vendor master that drops to non-root workers (OH-3) is the
exception path proposed in security/0003 §1 (doc-platform-core #68).

How to add an entry: PR with the row filled (why / containment / review date); approval = the
owner's name + date in the Approval column, written by the owner in the same PR. Review = re-check
the "why" still holds (e.g. an upstream rootless image appeared) before the review date.
