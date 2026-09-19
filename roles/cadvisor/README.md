# role: cadvisor

Per-container metrics — CPU, memory, network and filesystem **per container** — on every Docker host (inventory group `docker_hosts`). The node exporter covers the host; this covers what runs on it, so a container that leaks memory or keeps restarting is visible and alerted.

| Concern | How |
|---|---|
| Image | `ghcr.io/google/cadvisor:<v>` (pinned; guarded in CI). |
| Exposure | bound to the host's SVC address on port 9180 (8080 is taken on several hosts); ufw accepts the monitoring host only. |
| Scope | `--docker_only`, a reduced metric set (see `cadvisor_disable_metrics`), compose project/service labels kept so series are readable. |
| Drift | the role **asserts** each member has a Docker socket: a wrong inventory group fails the play instead of scraping nothing. |
| Scrape + alerts | Prometheus job `cadvisor`; rules `ContainerRestarting` and `ContainerMemoryNearLimit` (group `platform-containers`). |
| k3s | the cluster node runs containerd, not Docker: its pods are covered by the kubelet and their logs by promtail (`/var/log/pods`). |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/cadvisor.yml
ansible-playbook -i inventories/prod/hosts.yml playbooks/monitoring.yml     # picks up the new targets
```
