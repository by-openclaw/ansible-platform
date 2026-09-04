# role: verdaccio

npm registry + upstream proxy on `lxc-verdaccio-01` (`npm.<domain>`, VPN-only). **Official** `verdaccio/verdaccio:6.9.3` (node 24) + two supported plugins baked into a platform image built on the host (`templates/Dockerfile.j2`, the plugins' documented install): `verdaccio-aws-s3-storage` (verdaccio org, AWS SDK v3) and `verdaccio-openid` (Authentik OIDC, browser + `npm login` web flow). Composed through `service_scaffold` (mailbox, Traefik, S3 bucket, SSO assert).

- **Storage**: packages + package db in SeaweedFS bucket `verdaccio` — identity minted Vault-native by the scaffold (`prod/verdaccio/s3`), fed to the container as `AWS_*` env (config file holds no secrets). Local `/opt/verdaccio/storage` = openid token store only.
- **Auth**: humans = Authentik OIDC app `verdaccio` (access group `verdaccio-users`, enforced at the IdP **and** by the plugin's `authorized-groups`, which also lists the svc account **by name** — the plugin's gate admits `username === group`, and htpasswd users carry no groups; creds Vault `prod/verdaccio/oidc`, written by `roles/authentik`). Machines = one svc account `svc-verdaccio-prod` (htpasswd, Vault `prod/verdaccio/registry`, `keep-passwd-login`) used with Basic auth by CI/runner. `max_users: -1` → registration (and npm's legacy login) disabled by design.
- **Upgrade**: bump `verdaccio_image` (official tag) and/or a plugin pin, then `verdaccio_platform_rev` → the play rebuilds + restarts. Config changes restart the container (no hot reload).
- Internal Authentik name is `authentik.<domain>`; `npm.<domain>` needs the split-DNS record (catalog, PR #274) for SVC consumers.

Run: `ansible-playbook -i inventories/prod playbooks/verdaccio.yml` (after `playbooks/authentik.yml` has minted the OIDC client).

## Backup & restore

Class **C**: packages live in S3 (offsite `filer.backup`); the guest is disposable. Restore = run the play. Full matrix: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `docker logs verdaccio` must show `plugin verdaccio-aws-s3-storage successfully loaded (storage)`, `verdaccio-openid … (authentication)` and `OpenID Connect configuration discovery completed successfully`; `GET /-/ping` 200.
- SSO check: `GET /-/oauth/authorize` → 302 to `authentik.<domain>/application/o/authorize/?client_id=…`. `npm login --registry https://npm.<domain>` (npm ≥9) opens the browser flow.
- CI auth: registration is disabled (`max_users: -1`), so the svc account uses **Basic auth** — `.npmrc`: `//npm.<domain>/:_auth=<base64 user:password>` + `always-auth=true` (password from Vault `prod/verdaccio/registry`). `npm login` for humans = the OIDC web flow.
- Common: `Could not discover OpenID configuration` → provider-host unresolvable/blocked from the host; `AccessDenied` on S3 → identity/bucket mismatch (re-run play; the scaffold reconciles the SeaweedFS identity).
