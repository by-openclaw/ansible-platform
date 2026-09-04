# role: verdaccio (npm registry)

Verdaccio **6.2.0** on `lxc-verdaccio-01` (`10.1.3.191`, `npm.<domain>` VPN-only). Hosts the `@by-systems` scope, **proxies + caches npmjs**; every package `$authenticated`. First service born through `service_scaffold`.

- Admin user `svc-verdaccio-prod` (htpasswd) — credential in Vault `prod/verdaccio/registry`. Storage `/opt/verdaccio/storage` (local, v1).
- Uplink split is the 'global endpoint': own scope local, rest → npmjs. Clients: `.npmrc` `registry=https://npm.<domain>/` + a token.
- Follow-ups: S3 storage (SeaweedFS) + `verdaccio-openid` (Authentik-gated UI) — both need an in-container plugin build.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/verdaccio.yml`

## Backup & restore

Class **A**: storage dir in PBS. (S3 storage would move it to class C.) Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `/-/ping` 200 (backend + edge); unauth fetch **401** is correct; authed fetch serves upstream metadata.
- Common: `user registration disabled` on login → `max_users: -1` also blocks login; keep the default and gate via the openid plugin.
