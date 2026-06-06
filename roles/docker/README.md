# role: docker

Container runtime for nested service LXCs. Installs Debian's `docker.io` engine
(reproducible / pinned by the release — no external apt repo) plus
`python3-docker` (the SDK that `community.docker` modules need), configures
json-file log rotation, and enables the service.

Requires the LXC to have `features.nesting=true` (set in terraform).

Depends on `base`. Used by `pgadmin` (and any future Docker-hosted service).
