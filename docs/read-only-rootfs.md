# Read-only root filesystems (SEC-22) — register

`security/0003-hardening` (SEC-22): a container runs on a read-only root filesystem; what it
must write goes to a volume or a declared tmpfs. Every service audit recorded "writable rootfs"
as a platform gap. This file is the platform pass on it: what is read-only, what will be, and
what cannot be with the vendor's image.

Baseline 2026-10-04: 155 running containers, none read-only. Method: `docker diff <container>`
lists what a container wrote to its own layer since it started — the write set a read-only
root filesystem has to cover.

## How a service opts in

A container definition handed to `roles/service_scaffold` declares:

```yaml
read_only: true
tmpfs: ["/tmp:rw,size=64m"]        # add `exec` when the image runs helpers from there
cap_drop: [ALL]                     # only when the image's binary carries no file capability
security_opts: ["no-new-privileges:true"]
```

The definition is authoritative for these four options: an option that is not declared is set
to its neutral value and compared strictly, so removing a line reverts the container. A change
is applied one service at a time and verified in the service's log before the next one.

## Read-only today

| Container | Hosts | Writable paths | Verified |
|---|---|---|---|
| `cadvisor` | every Docker host | none (host mounts are read-only) | `/healthz` 200, container series exported |
| `kroki`, `kroki-mermaid`, `plantuml` | `lxc-diagrams-01` | tmpfs `/tmp` | real renders (Graphviz, Mermaid, PlantUML) |
| `verdaccio` | `lxc-verdaccio-01` | host directories (storage, configuration), tmpfs `/tmp` | `/-/ping` 200, no error in the log |
| `vaultwarden` | `lxc-vaultwarden-01` | the data volume, tmpfs `/tmp` | `/alive` 200, `/api/config` 200 |
| `grafana` | `lxc-monitoring-01` | host directories (data, logs), tmpfs `/tmp` with `exec` (plugin helpers) | `/api/health`: database ok |
| `step-ca` | `lxc-stepca-01` | the state volume, tmpfs `/tmp` | `/health` ok, `/roots.pem` 200 |

`step-ca` keeps its capabilities: its binary carries a file capability and does not start
without it in the bounding set (`cap_drop: ALL` → "Operation not permitted", 2026-10-04).

## Next (same method, one service at a time)

The cluster components are read-only from their first start (their own change): `etcd`,
`postgres` (Patroni), `postgres-exporter`, `redis`, `redis-sentinel`, `dbproxy`.

Candidates whose write set is empty or temporary files only: `prometheus`, `loki`,
`alertmanager`, `blackbox-exporter`, `seaweedfs` (three containers), `traefik`, `vault`,
`adguard`, `crowdsec`, `authentik-ldap`, `nextcloud-exporter`, `netbird-relay`,
`netbird-signal`, `netbird-management`, `ciso-assistant-frontend`. The edge, the secret store
and the object store are done in a window, each on its own.

## Cannot be read-only with the vendor's image

The entrypoint rewrites paths inside the image at every start (configuration rendered into
`/etc`, a supervisor's state, certificates injected into the trust store). A tmpfs cannot
replace a directory that also carries the image's own files.

| Container(s) | What is written |
|---|---|
| `gitlab` (Omnibus) | `/etc`, `/opt/gitlab` — runit and the rendered configuration of ten services |
| the Jitsi containers | `/config`, `/etc/cont-init.d`, `/etc/services.d` (s6-overlay) |
| the Harbor containers (except its Redis) | `/etc/pki`, `/harbor_cust_cert`, per-service `/etc/<name>` |
| the JumpServer containers | `/opt/<component>`, `/run` (supervisors), nginx configuration |
| the Mailcow stack (20) | `/etc/<service>`, hooks, supervisord — vendor compose |
| `onlyoffice`, `collab-talk`, `collab-talk-recording`, `collab-whiteboard` | `/etc/onlyoffice`, `/conf`, `/app/data` |
| the Wazuh containers | `/etc/cont-init.d`, `/var/ossec`, `/usr/share` |
| `netbox`, `netbox-worker`, `netbox-housekeeping` | `/etc/netbox`, `/opt/netbox` |
| `nextcloud`, `nextcloud-cron` | Apache run state, PHP sessions, `/var/www` |
| `drawio` | Tomcat configuration under `/usr/local` |
| `portainer-agent` (every Docker host) | its TLS key pair, generated into `/app` at start |
| `pgadmin` | `/pgadmin4` (rendered configuration, server list) |

These stay writable until the vendor supports a read-only root filesystem; the containment is
the one their root override already records (`docs/override-hardening.md`) plus pinned images.
