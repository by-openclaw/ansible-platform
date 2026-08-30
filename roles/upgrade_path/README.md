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

1. Detect the running version (`upgrade_path_current_cmd`).
2. Drop every rung at or below it — so a re-run is a no-op, never a downgrade.
3. For each remaining rung, in order:
   - point the service's own image variable at that rung and re-run **its role**
     (so the upgrade takes the normal deploy path, leaving no hand-made container)
   - run the migration command and wait for it to finish
   - run the health gate
   - confirm the reported version actually moved, and **halt the whole path** if it did not

`any_errors_fatal` plus the per-rung gate means a failure stops the climb.

## Key parameters

| Variable | Purpose |
|---|---|
| `upgrade_path_steps` | Ordered rungs: `{version, image, note}` |
| `upgrade_path_current_cmd` | Shell command printing the running version |
| `upgrade_path_role` | The service's own role, re-run per rung |
| `upgrade_path_image_var` | Name of that role's image variable, e.g. `nextcloud_image` |
| `upgrade_path_migrate_cmd` | Migration that must complete before the next rung |
| `upgrade_path_verify_cmd` | Health gate; non-zero stops the climb |
| `upgrade_path_apply` | Defaults `false` — dry run prints the ladder only |

`vars:` on `include_role` must be a literal dictionary, so the per-service image
variable is set by name with `set_fact` (which does accept a templated key).
That is what keeps this role service-agnostic.

## Example — Nextcloud (in use)

See `playbooks/nextcloud-upgrade.yml`. Verified live: `33.0.5 → 33.0.8 → 34.0.3`,
each rung migrated and health-checked before the next.

## Example — GitLab (for when it is provisioned)

GitLab's required stop-overs come from its own upgrade path tool; encode them as
rungs. The shape is identical, only the commands change:

```yaml
- role: upgrade_path
  vars:
    upgrade_path_service: gitlab
    upgrade_path_role: gitlab
    upgrade_path_image_var: gitlab_image
    upgrade_path_steps:
      - { version: "17.3.7", image: "gitlab/gitlab-ce:17.3.7-ce.0", note: "required stop-over" }
      - { version: "17.5.5", image: "gitlab/gitlab-ce:17.5.5-ce.0", note: "required stop-over" }
      - { version: "17.8.7", image: "gitlab/gitlab-ce:17.8.7-ce.0", note: "required stop-over" }
    upgrade_path_current_cmd: >-
      docker exec gitlab gitlab-rake gitlab:env:info 2>/dev/null
      | awk '/GitLab information/{f=1} f&&/Version:/{print $2; exit}'
    # Background migrations MUST drain before the next hop, or the following
    # upgrade starts against a half-migrated schema.
    upgrade_path_migrate_cmd: >-
      docker exec gitlab gitlab-rake db:migrate &&
      docker exec gitlab gitlab-rake gitlab:background_migrations:finalize_all
    upgrade_path_verify_cmd: >-
      docker exec gitlab gitlab-rake gitlab:check SANITIZE=true
    upgrade_path_settle_seconds: 120
```

Always take a backup before a major hop — a failed migration is restored, not retried.
