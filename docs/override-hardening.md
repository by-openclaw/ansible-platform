# Hardening overrides — processes that run as root

`security/0003-hardening` §1: every container process runs as a non-root UID; an exception needs
explicit written approval, documented here, reviewed annually. This file is the register. An
entry is valid only with an approval line; a missing or expired approval = the exception is void
and the service is non-compliant.

| # | Service / container | Hosts | Why root is required | Containment | Approval | Review by |
|---|---|---|---|---|---|---|
| OH-1 | `cadvisor` (`roles/cadvisor`) — container metrics agent | every Docker host | Reads the kernel's cgroup/namespace accounting of *other* containers: `/sys/fs/cgroup`, `/var/lib/docker` (overlay metadata), `/dev/disk`; a non-root UID cannot read other containers' cgroup files. Upstream ships and documents the image root-only. | `privileged: false`; every host mount **read-only** (`/`, `/var/run`, `/sys`, `/var/lib/docker`, `/dev/disk`); no capabilities added; `--docker_only`; listens on the SVC address only, ufw admits the Prometheus scrapers only; pinned image. | **pending — @yboujraf** | 2027-10-01 |
| OH-2 | `portainer-agent` (`roles/portainer`) — console agent | every Docker host | Talks to the Docker daemon through `/var/run/docker.sock` and browses `/var/lib/docker/volumes`; the socket is root-owned and the Docker API is root-equivalent by design — a non-root UID in the container changes nothing about what the socket grants. | Reachable from the Portainer console host only (ufw + `AGENT_SECRET`); the console itself is behind Traefik + Authentik SSO (`portainer-admins`); pinned image; journald logging. Removing the agent = losing the fleet console. | **pending — @yboujraf** | 2027-10-01 |

Not an exception: `node_exporter` runs as a native service user; service containers
(Authentik, GitLab, Nextcloud, …) run with their non-root UIDs — a service that needs root is a
finding, not an entry here.

How to add an entry: PR with the row filled (why / containment / review date); approval = the
owner's name + date in the Approval column, written by the owner in the same PR. Review = re-check
the "why" still holds (e.g. an upstream rootless image appeared) before the review date.
