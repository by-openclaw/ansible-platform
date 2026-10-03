# k3s — service page

Catalog row: `inventories/prod/group_vars/all/services.yml` (`name: k3s`). Role `roles/k3s`, play `playbooks/k3s.yml`, guest `vm-k3s-01` (VM — a real kernel for the kubelet). Audit: [`docs/audits/k3s-2026-10-03.md`](../audits/k3s-2026-10-03.md).

## Identity (identity/0002 §per-tool identity doc)

1. **ADR:** `identity/0001-authentication` — the published applications sit behind the platform Traefik with Authentik forwardAuth (`k3s_published_apps`); the API (`:6443`) is reached with kubeconfigs only: the node's admin kubeconfig (`0640` root) and one CI deployer service account per namespace (`k3s_ci_namespaces`) whose kubeconfig is minted into Vault and pushed as a masked GitLab CI variable.
2. **Authentik application:** none for the API; the apps' routes (`demo`) use the forwardAuth middleware.
3. **Access model:** `cluster-admin` = `system:masters` (the node kubeconfig, break-glass on the host), the Helm controller SAs, the Portainer agent SA (vendor; OH-2); CI deployers are namespace-scoped. Pod Security Admission: `demo`/`default` **restricted**, `portainer-agent` baseline (`k3s_pod_security`).
4. **Vault paths:** `secret/{env}/k3s/ci-<namespace>` (deployer kubeconfig, base64).
5. **Ansible adapter + vars:** `roles/k3s` (`defaults/main.yml`: pin `k3s_version` + `k3s_sha256`, CIDRs, disabled components, registry mirror through Harbor, audit log, Pod Security, CI namespaces, published apps; `templates/config.yaml.j2`, `audit-policy.yaml.j2`, `k3s.service.j2`, `registries.yaml.j2`; `tasks/ci-namespace.yml`).
6. **Removal notes:** `playbooks/decommission-service.yml`; class B — the cluster state (sqlite under `/var/lib/rancher/k3s/server/db`) lives in the PBS guest image; workloads are declared by their own repositories (GitLab CI).

## Notifications (services/0005)

1. **Transport:** none — k3s sends no mail.
2. **What is sent:** nothing to operators.
3. **Alerting path:** Prometheus `node` + the blackbox probe of `k3s.<domain>` → Alertmanager → Discord/mail; the API server and kubelet metrics (token-protected) and kube-state-metrics are the monitoring pass's item.
4. **Logs:** journald (k3s, containerd) + pod logs (`/var/log/pods`, promtail `k3s_pods`) + the **API audit log** (`/var/log/k3s/audit.log`, Metadata level, promtail `k3s_audit` with the `audit` label) → Loki.
5. **Operator contact:** `docs/register.md` row.

## Backup (infra/0008)

Class B (`docs/backup.md`): the cluster datastore (sqlite) and the certificates in the PBS guest image (daily); workloads are redeployable from their repositories (demo pipeline). Restore = PBS image, or `k3s.yml` + the CI pipelines.

## Operations: Headlamp (web UI) and k9s (CLI) — infra/0001 §1

- **Headlamp** `headlamp.<domain>` (internal only): runs in the cluster (namespace `headlamp`, Pod Security `restricted`, read-only root filesystem) and has **no rights of its own**. A person signs in through Authentik (OIDC application `headlamp`, restricted to the platform admins group); the API server validates that token itself (`kube-apiserver --oidc-*`, users and groups prefixed `oidc:`), and the cluster binds the group `oidc:<platform admins>` to `cluster-admin`. Every action appears in the API audit log under the person's name. Client id and secret: Vault `secret/{env}/k3s/headlamp-oidc` (minted by the authentik play — run it before `k3s.yml` on a new platform).
- **k9s** on the node (`/usr/local/bin/k9s`, pinned release, checksum verified): the terminal UI on the node's admin kubeconfig — break-glass and day-to-day CLI through the bastion.
- Portainer keeps its agent in the cluster for the container console; Headlamp is the Kubernetes-native view (workloads, RBAC, events, logs).
