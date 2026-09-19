# role: k3s

Single-node k3s on `vm-k3s-01` (SVC): the application platform. GitLab CI builds with Kaniko, pushes to the project registry, and a namespace-scoped deployer applies Kubernetes manifests; apps are published as `<app>.apps.<domain>` through the **platform** Traefik (TLS, forwardAuth SSO) which forwards plain HTTP to the k3s ingress (embedded Traefik, servicelb on :80).

## Contract map

| Concern | How |
|---|---|
| Install | pinned release binary (`k3s_version`, sha256 verified), **unit rendered by the role** (no vendor install script), `config.yaml` declared (`tls-san`, CIDRs, secrets encryption, anonymous auth off). |
| Registries | `registries.yaml`: Docker Hub mirrored through the Harbor pull-through cache (`dockerhub/` rewrite). Project images come from the GitLab registry with a per-project deploy token (pull secret created by the deploy job). |
| Access for CI | per namespace (`k3s_ci_namespaces`): ServiceAccount `gitlab-deployer`, RoleBinding to `admin` in that namespace only, long-lived token; kubeconfig → Vault `prod/k3s/ci-<ns>` and → the project's CI variable `KUBECONFIG_B64` (masked, protected). |
| Ingress | FW rule `PASS DMZ Traefik→SVC k3s ingress` (:80), one `traefik_route` per app (`k3s_published_apps`, internal-only + forwardAuth, unbound override per app name), Authentik proxy app per app. |
| Backup | class A for the VM (PBS). Persistent volumes: local-path; Velero to S3 is the next step before any stateful app. |
| Probes | `blackbox_tcp` on `:6443`, HTTPS probe on each published app (Traefik host list). |
| Version | `k3s_version` moves through an upgrade ladder (one minor at a time), never a bare bump. |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/k3s.yml
```

## Runbook

- `kubectl get nodes`, `kubectl -n demo get all`; ingress answers `curl -H 'Host: demo.apps.<domain>' http://10.1.3.195/`.
- A deploy job fails with 401 on the API → the SA token was recreated: re-run the play (Vault + CI variable refresh with `vault_secret_force_fields`).
- Image pull errors → the deploy token (`k3s-pull`) or the Harbor mirror; `crictl pull` on the node shows which.
