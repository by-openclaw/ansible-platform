# roles/ciso_assistant

[CISO Assistant](https://intuitem.gitbook.io/ciso-assistant/) (intuitem, AGPLv3) — the platform's
compliance registry, named by `doc-platform-core` ADR `security/0002` and never deployed until now.
Git stays the source of truth for decisions; this is the source of truth for **posture**.

The product is *CISO Assistant*; the platform **service** it provides is `grc`
(`naming/0002 §3 {function}`). One name everywhere: host `lxc-grc-01`, route `grc.<domain>`, mailbox
`grc@<domain>`, database and S3 identity `grc`, Vault `prod/grc/*`, firewall aliases `host4_grc` /
`port_grc`, SSO slug `grc`. `ciso_assistant_service` is that single source — nothing is spelled out
twice.

| Concern | How |
|---|---|
| Platform concerns | `roles/service_scaffold` (docs/new-service.md golden path) composes database, S3, Vault secrets, mailbox and the Traefik route from one contract. |
| Images | `backend` + `frontend` at an exact tag (`ciso_assistant_version`), never `:latest`. The task worker runs the backend image with the Huey entrypoint. |
| Database | Shared PostgreSQL cluster, credential in Vault, `sslmode=verify-full`. The image ships no CA store where libpq looks, so the host bundle is mounted at `/home/app/.postgresql/root.crt`. |
| Evidence | SeaweedFS S3, never the guest's disk — so a rebuilt guest loses nothing. |
| Secrets | `DJANGO_SECRET_KEY` minted in Vault (`prod/grc/app`); rotating it invalidates every session. |
| Mail | Service mailbox `grc@<domain>` — the superuser invitation is sent from it. |
| Exposure | `private`: Traefik, internal only, split-DNS to the proxy. Only Traefik reaches the two published ports (host firewall). |
| SSO | Authentik native OIDC, **written by this role** (see below). Access group `grc-users`, accounts provisioned just-in-time. |
| Observability | `LOG_FORMAT=json` for Loki, `EXPOSE_METRICS=True` for Prometheus, audit log kept 365 days (compliance evidence outlives the 90-day default). |

## Two routes, one hostname

The frontend renders server-side and reaches the backend by container name on the private network.
The browser *also* calls the API on the same public name, and the frontend container does not serve
that path — so `/api` is routed to the backend port directly. Both ports therefore carry a firewall
rule from the proxy.

The container name the frontend calls must appear in the backend's `ALLOWED_HOSTS`, or Django
answers every request with 400 while looking perfectly healthy. One variable feeds both.

## SSO is not a manual step

The tool keeps its identity-provider configuration in its own tables (`global_settings`, rows
`sso` and `feature-flags`; `iam_idpgroup` and its link to the tool's groups), which is why upstream
documents it as a UI task. Its database is on the shared PostgreSQL, so `tasks/sso.yml` writes
them with one transaction of plain SQL on the cluster's leader: values reach `psql` on standard
input (the client secret is on no command line and the server is told not to log the
statements), a row is written only where it differs, and a dry run executes the same statements
and rolls them back — it reports what a run would write. The application creates the `sso` row
itself, with its defaults; the role only merges into it.

Two things besides the binding, or a sign-in ends in "SSO authentication failed": the
`jit_provisioning` feature flag (the setting alone is inert) and an identity-provider group
bound to one of the tool's groups (`ciso_assistant_group_map`) — membership decides who
administers the registry, nobody is granted anything by name.

The callback path is read from the application's own routes rather than guessed: `core/urls.py`
mounts `accounts/oidc/` and django-allauth appends `<provider_id>/login/callback/`. The provider id
in `roles/ciso_assistant` defaults and the redirect URI in `authentik_oidc_apps` must agree.

Local login stays available alongside SSO (`ciso_assistant_oidc_force: false`). This is the tool
that documents the break-glass procedure, so it must not be the one service that locks its
administrators out when the identity provider is down.

`GRC-01` in `roles/contract_audit` enforces the binding fleet-wide.

## After it runs

1. Import the framework libraries (ISO 27001:2022, NIS2, GDPR) from the catalog.
2. One perimeter per service, mirroring `docs/register.md`.
3. Feed the `CISO mapping` tables from the ADRs as applied controls; evidence links back to the role
   README, the service document and the contract-audit scorecard.
