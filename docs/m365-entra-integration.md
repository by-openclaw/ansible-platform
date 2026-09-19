# Microsoft 365 / Entra ID integration — design (PARKED)

Status: **parked** (2026-09-19). The platform's own domain has no M365, Exchange or Entra ID tenant, so nothing here is deployed. The design, the permissions and the secret template are recorded now so a customer tenant can be wired in without rediscovery. Secret template: controller `~/.openclaw/workspace/infra/secrets/_shared/app-m365-TEMPLATE.json` (never in git); Vault path `m365/<domain-slug>`.

## Scope (what the automation must be able to do, per customer domain)

| Capability | Mechanism | Role to build |
|---|---|---|
| Entra ID ↔ Authentik, bidirectional users + groups | Authentik **Entra ID source** (tenant → Authentik: users, groups, membership) + Authentik **Entra ID provider** (Authentik → tenant: create/update users and groups, group-based). The people file stays the single source; the identity orchestrator decides per person `idp: entra` or `idp: authentik`. | `authentik` (source/provider blueprints), `identity_orchestrator` |
| Mailbox with license (create / update / retire) | Graph: create user, `assignLicense` with the SKU from the catalog, mailbox settings; retire = remove license, convert to shared, forward, block sign-in (never delete — archive). Unlicensed people stay on mailcow (split domain: separate parked design). | `m365_identity` |
| GAL fed like the Nextcloud address book | Exchange Online `New-MailContact` / `Set-MailContact` for external contacts (Graph cannot create org contacts); Graph `orgContacts` + `users` read for the Nextcloud Company address book (same vCard source as today). | `m365_gal` |
| Teams sessions (meetings, teams, channels) | Graph online meetings (application access policy), teams/channels CRUD from the team bindings (same list that drives the Nextcloud team folders and Talk rooms). | `m365_teams` |
| SharePoint intranet (sites, libraries, permissions) | Graph sites (team sites via the M365 group, communication sites via the SharePoint admin API), `Sites.Selected` where possible. | `m365_sharepoint` |

Convergence rule: the **people file and the team bindings drive both worlds**. A team = Authentik group + Nextcloud folder/room/calendar + (when the domain has M365) an Entra group, a Team and a SharePoint site. No per-tenant hand configuration.

## Identity

- App registration `svc-ansible-m365-<domain-slug>`, single tenant, **certificate credential** (key generated on the controller, stored only in Vault), client secret only as fallback with its expiry recorded.
- Graph **application** permissions (admin consent), `Exchange.ManageAsApp` for the Exchange cmdlets, Entra roles on the service principal (User, Groups, License, Exchange, Teams, SharePoint administrators) — assigned only for the capabilities enabled in the catalog. Full list in the template's `_permissions`.
- All calls run from the controller through a pinned PowerShell container (`Microsoft.Graph`, `ExchangeOnlineManagement`, `MicrosoftTeams`, `PnP.PowerShell`) or the Graph REST API from Ansible `uri`; every write is drift-gated (read → compare → write) and dry-run capable.

## Setup steps (mirror of the template's `_steps`)

1. App registration → client id, tenant id.
2. Certificate: generate on the controller, upload the public part, record thumbprint and expiry.
3. Graph application permissions + `Exchange.ManageAsApp` → grant admin consent.
4. Entra roles on the service principal.
5. Teams application access policy for online meetings.
6. SharePoint admin URL.
7. License SKU ids from `subscribedSkus`.
8. Mirror the file to Vault (`vault-kv-sync.yml`, `vault_kv_map.yml`), roles read only from Vault.
9. Read-only acceptance probe before any write capability is enabled.

## Acceptance (read-only probe, first thing to build)

`playbooks/m365-probe.yml`: token with the certificate → `organization`, `subscribedSkus`, `users?$top=1`, `groups?$top=1`, `sites/root`, Exchange `Get-AcceptedDomain`. Prints counts only. Done when all six answer with the app identity.

## Not in scope here

- Split-domain mail flow (Exchange internal relay → mailcow for unlicensed users): separate parked design, only on request.
- Device management (Intune): stays with the customer's tenant.

## NIS2 notes

Least privilege per capability, certificate auth, consent recorded, credential expiry in Vault, every action logged by the platform run (Loki) and by the tenant (audit log). The service principal has no interactive sign-in.
