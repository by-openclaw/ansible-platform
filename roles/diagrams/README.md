# role: diagrams (Kroki · drawio · PlantUML)

Shared rendering on `lxc-diagrams-01`: Kroki **0.28.0** (+mermaid), PlantUML server, drawio **24.7.17**. Used by GitLab wiki/docs, NetBox, admin portal. Internal-only route (`drawio.<domain>` — SSO forwardAuth pending the SSO ruling).

- Ports: kroki 8000, plantuml 8004, drawio via Traefik.
- Stateless; containers ride journald.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/diagrams.yml`

## Backup & restore

Class **D** — nothing to back up; rerun the play. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: edge `drawio.<domain>` 200; `docker ps` 4 containers.
- Common: Kroki mermaid failures → the companion `kroki-mermaid` container.
