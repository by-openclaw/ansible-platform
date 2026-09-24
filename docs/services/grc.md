# Compliance registry (CISO Assistant) — Setup Runbook

The platform's authoritative compliance registry: framework catalogs (ISO/IEC 27001:2022, NIS2, GDPR
and the mappings between them), perimeters, applied controls and evidence. ADR `security/0002` named
it and it went undeployed, so the `CISO mapping` table every ADR carries had nowhere to land.

Git stays the source of truth for **decisions**. This is the source of truth for **posture**.

The product is *CISO Assistant* (intuitem, AGPLv3). The platform service is `grc`
(`naming/0002 §3 {function}`), and that one name runs through the host, route, mailbox, database,
S3 identity, Vault paths, firewall aliases and SSO slug.

## 1. Image decision

`ghcr.io/intuitem/ciso-assistant-community/backend` and `.../frontend`, both at an exact tag from
`ciso_assistant_version` — never `:latest`. The task worker runs the **backend** image with the Huey
entrypoint, so the stack is two images, three containers.

## 2. Services architecture

| piece | where | how |
|---|---|---|
| backend (API, migrations on start) | `lxc-grc-01`, port 8000 on the SVC address | `community.docker.docker_container` |
| task worker | same host, same image, `run_huey` entrypoint | same |
| frontend (server-side rendered) | same host, port 3000 on the SVC address | same |
| private network | `ciso-assistant`, **IPv4-only by design** | `community.docker.docker_network` |
| routes | `grc.<domain>` and `grc.<domain>/api` on the platform Traefik, internal-only | `service_scaffold` → `traefik_route`, plus a second route for the API path |

The frontend renders every page server-side by calling the backend **by container name** on the
private network. The browser additionally calls `/api` on the same public name, and the frontend
container does not serve that path — hence two routes and two firewall rules for one service.

The network is deliberately IPv4-only: the daemon's `fixed-cidr-v6` covers the default bridge, not a
user-defined one, so an IPv6 address here has no route out and the database's AAAA record would be
tried and time out on every connection.

## 3. Pre-requisites

- Guest provisioned by Terraform (`infra-terraform-proxmox environments/prod/svc-grc.tf`, vmid 545,
  10.1.3.145 / fd01:3::145, 2 cores / 4 GiB / 16 GiB).
- Inventory: host in group `ciso_assistant`, which is a child of `cluster` and of `docker_hosts`.
  The `cluster` membership is what makes fleet hardening, log shipping, the security agent and the
  contract audit reach it — without it the host is silently skipped.
- Shared PostgreSQL, SeaweedFS, Vault, mailcow and Authentik running.

## 4. Secrets (Vault KV paths)

| path | fields | who writes |
|---|---|---|
| `prod/grc/app` | `django_secret_key` | `service_scaffold` → `vault_secret` (get-or-create). Rotating it invalidates every session. |
| `prod/grc/db-pgsql` | `password` | `service_scaffold` → `postgres_db` |
| `prod/grc/s3` | `access_key`, `secret_key`, `endpoint` | `service_scaffold` → `seaweedfs_bucket` |
| `prod/grc/oidc` | `client_id`, `client_secret` | `roles/authentik` (Vault-native app) — consumed by this role |
| `prod/mail/grc` | mailbox credential | `service_scaffold` → `mailbox` |

## 5. Certificates

None on the service. TLS terminates on the platform Traefik (Let's Encrypt wildcard). The database
is reached with `sslmode=verify-full`; the image ships no CA store where libpq looks, so the host
bundle is mounted read-only at `/home/app/.postgresql/root.crt`.

## 6. Configuration source

`roles/ciso_assistant/defaults/main.yml` — version, ports, container names, Vault paths, SSO
endpoints, probe patience. `ciso_assistant_service` is the single source for the service identity.

## 7. Provisioning

`roles/service_scaffold` composes database, S3 bucket and identity, Vault secrets, mailbox and the
app route from one contract. The role then starts the three containers, declares its host-firewall
rules, publishes the API path and binds SSO.

## 8. Exposure / routing

Private class: internal-only Traefik routes, split-DNS `grc` → the proxy (both A and AAAA), and
OPNsense rules that let **only** Traefik reach ports 3000 and 8000 on the guest. No public record.

## 9. Installation steps

1. `terraform apply` the guest, then bootstrap it with `playbooks/identity-baseline.yml`.
2. `ansible-playbook playbooks/authentik.yml` — mints the OIDC client into `prod/grc/oidc`.
3. Apply the firewall catalog scoped:
   `ansible-playbook playbooks/opnsense.yml -e '{"opn_fw_only": ["port_grc", "port_grc_api", "host4_grc", "host6_grc", "PASS DMZ Traefik→SVC CISO Assistant (reverse proxy)"]}'`
4. `ansible-playbook playbooks/opnsense-unbound-overrides.yml` — split-DNS record.
5. `ansible-playbook playbooks/ciso-assistant.yml`
6. Fleet baseline on the new host: `playbooks/promtail.yml`, `playbooks/wazuh.yml`,
   `playbooks/hardening.yml` (this one enables ufw — the service rules are already stored).
7. Re-run step 5: it must report `changed=0`.

**First boot is slow on purpose.** The backend applies ~170 migrations and then imports the whole
framework catalog before it serves anything — minutes, not seconds. The role's API probe waits
(`ciso_assistant_api_probe_retries` × `ciso_assistant_api_probe_delay`, 15 minutes by default) and
only then tests the login page. Every later run answers on the first try.

## 10. Post-install configuration

1. Import the framework libraries from the catalog (ISO 27001:2022, NIS2, GDPR).
2. One perimeter per service, mirroring `docs/register.md`.
3. Feed the `CISO mapping` tables from the ADRs as applied controls; evidence links back to the role
   README, the service document and the contract-audit scorecard.

## 11. Upgrade procedure

Bump `ciso_assistant_version`, re-run the play. Both images move together; the backend runs
migrations on start, so read its log before declaring the upgrade done. Back up the database first
(see `docs/backup.md`) — migrations are not reversible.

## 12. Health checks

- `GET /api/health/` on the backend port → 200 (also the container healthcheck).
- `GET /login` on the route → 200.
- `GET /api/settings/sso/info/` → `is_enabled: true` (contract-audit row `GRC-01`).
- `GET /api/_allauth/browser/v1/config` lists the provider and its discovery URL.
- cAdvisor on the guest, node exporter, promtail → Loki, security agent reporting.

## 13. Troubleshooting

| symptom | cause | fix |
|---|---|---|
| every page 400, backend healthy | the container name the frontend calls is not in the backend's `ALLOWED_HOSTS` | one variable feeds both — see the role defaults |
| login page 500, `SyntaxError: Unexpected token '<'` | the backend answered HTML to an API call; read the backend log for the real error | fix the underlying 400/500 |
| login page 500, `KeyError('sp')` | the SSO settings block was replaced instead of merged, dropping the SAML defaults the info endpoint reads | re-run the play; `sso_bind.py.j2` repairs the row |
| `connection failed: root certificate file … does not exist` | CA bundle not mounted | `ciso_assistant_ca_bundle` → `ciso_assistant_container_ca_path` |
| frontend cannot reach the backend, IPv6 timeout | user-defined network given IPv6 with no route | the network is IPv4-only by design |
| probe fails on a first install | migrations and catalog import still running | raise `ciso_assistant_api_probe_retries`; check the backend log |

## 14. Identity and access

Native OIDC against Authentik (`authentik_oidc_apps` slug `grc`, `restrict_to_group: true`, access
group `grc-users`). Accounts are provisioned just-in-time on first sign-in, so the identity provider
is the only gate on who gets one.

**The binding is written by the role, not clicked in the admin UI.** The tool keeps its
identity-provider configuration in a database row (`global_settings`, name `sso`), which is why
upstream documents it as a manual step. `templates/sso_bind.py.j2` is piped into `manage.py shell`
on standard input — keeping the client secret out of the guest's process list — and merges the OIDC
keys over the application's own SAML defaults.

Local login stays available (`ciso_assistant_oidc_force: false`). This is the tool that documents
the break-glass procedure; it must not be the one service that locks its administrators out when the
identity provider is down.

## 15. Notifications

Mailbox `grc@<domain>` (scaffold, delegates per the platform rule) sends the superuser invitation
and any notification the tool raises. Operational alerts about the guest come from the monitoring
stack, not from the application.
