# Role: `upgrade_path`

Step a service through major versions **one at a time**, with a migration and a
health gate between each rung.

## Why

Some products refuse to skip majors, and failing to respect that does not fail
loudly — it corrupts.

- **Nextcloud** must be on the *latest patch of its current major* before moving
  to the next, and runs database migrations per major via `occ upgrade`.
- **GitLab** is stricter: it publishes required stop-over versions, and each one
  must finish its background migrations before the next hop is safe.

Encoding the rule once means every service upgrades the same way, and a
half-migrated service never receives the next major.

## How it works

1. Detect the running version (`upgrade_path_current`: one command or one file, and an expression that extracts the version).
2. Drop every rung at or below it — so a re-run is a no-op, never a downgrade.
3. For each remaining rung, in order:
   - point the service's own image variable at that rung and re-run **its role**
     (so the upgrade takes the normal deploy path, leaving no hand-made container)
   - run the migration checks (`upgrade_path_migrate`) and wait for them to pass
   - run the health gate (`upgrade_path_verify`)
   - confirm the reported version actually moved, and **halt the whole path** if it did not

`any_errors_fatal` plus the per-rung gate means a failure stops the climb.

## Key parameters

| Variable | Purpose |
|---|---|
| `upgrade_path_steps` | Ordered rungs: `{version, image, note}` |
| `upgrade_path_current` | Where the running version is read: `argv` or `file`, optional `regex` (first group) and `suffix` |
| `upgrade_path_role` | The service's own role, re-run per rung |
| `upgrade_path_image_var` | Name of that role's image variable, e.g. `nextcloud_image` |
| `upgrade_path_migrate` | Checks (one command or one HTTP request each) that must pass before the next rung |
| `upgrade_path_verify` | Health gate: the same kind of checks; the first that fails stops the climb |
| `upgrade_path_apply` | Defaults `false` — a dry run prints the ladder and runs the read-only checks, so a gate that cannot work is found before an upgrade |

`vars:` on `include_role` must be a literal dictionary, so the per-service image
variable is set by name with `set_fact` (which does accept a templated key).
That is what keeps this role service-agnostic.

## Example — Nextcloud (in use)

See `playbooks/nextcloud-upgrade.yml`. Verified live: `33.0.5 → 33.0.8 → 34.0.3`,
each rung migrated and health-checked before the next.

## Checks

No shell: a check is one command (an argument list) or one HTTP request, with what its answer must
contain. `tasks/check.yml` runs one and gives the verdict.

```yaml
upgrade_path_current:
  argv: [docker, exec, -u, www-data, nextcloud, php, occ, status, --output=json]
  regex: '"versionstring":"([^"]+)"'          # first group = the version
upgrade_path_migrate:
  - name: "occ upgrade"
    argv: [docker, exec, -u, www-data, nextcloud, php, occ, upgrade, --no-interaction]
    tolerate_failure: true                    # a non-zero exit is not a failure
    changes: true                             # never run in a dry run
  - name: "no database upgrade pending"
    argv: [docker, exec, -u, www-data, nextcloud, php, occ, status, --output=json]
    stdout_regex: ['"needsDbUpgrade":false']  # every expression must be found
upgrade_path_verify:
  - name: "the application is ready"
    url: "http://127.0.0.1:8080/-/readiness"  # status 200 unless `status` says otherwise
  - name: "no runit service is down"
    argv: [docker, exec, gitlab, gitlab-ctl, status]
    stdout_not_regex: ['(?m)^down:']          # none of these may be found
```

The three ladders in use: `playbooks/nextcloud-upgrade.yml`, `playbooks/gitlab-upgrade.yml`,
`playbooks/harbor-upgrade.yml`.

Always take a backup before a major hop — a failed migration is restored, not retried.
