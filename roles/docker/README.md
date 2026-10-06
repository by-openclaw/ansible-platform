# role: docker

Container runtime for nested service LXCs. Installs Debian's `docker.io` engine
(reproducible / pinned by the release — no external apt repo) plus
`python3-docker` (the SDK that `community.docker` modules need), configures
json-file log rotation, and enables the service.

Requires the LXC to have `features.nesting=true` (set in terraform).

Depends on `base`. Used by `pgadmin` (and any future Docker-hosted service).

## Images of superseded versions

After an upgrade the previous version's image stays on disk. At each converge
(`tasks/superseded_images.yml`) an image is removed when no container uses it **and** another image
of the same repository is in use by a container on the host; untagged leftovers are pruned. An image
no running service relates to — the image a scheduled job pulls once and runs from a timer — is left
alone, so no job depends on the registry at run time. A rollback to the previous version pulls its
image again (tags are pinned).

`docker_superseded_images_remove: false` turns it off; `docker_superseded_images_keep` is a list of
regular expressions of image names never removed. `--check` lists what would go.
