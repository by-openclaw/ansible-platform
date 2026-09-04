# role: crowdsec (LAPI)

CrowdSec **v1.7.8** central LAPI on `lxc-crowdsec-01` (`:8080`, appsec `:7422`). 23 machines (agents everywhere via `crowdsec_agent`), bouncers on OPNsense (FW) + Traefik (L7 plugin). IPS = CrowdSec (+ Suricata WAN feed — enablement pending).

- Enrolment gotcha: `lapi status` rc=0 can be a false positive; a rebuilt host leaves a stale machine — delete before re-enrol.
- Logs self-rotate (`.gz` rotations); LAPI sqlite on the guest.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/crowdsec.yml`

## Backup & restore

Class **A**: sqlite (machines/bouncers) in PBS; decisions are ephemeral. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `cscli machines list` (all validated, fresh heartbeats), `cscli bouncers list` (recent `last_pull`), `cscli decisions list`.
- Common: bouncer not pulling → API key mismatch (`fabric/app-crowdsec-bouncer-*.json`).
