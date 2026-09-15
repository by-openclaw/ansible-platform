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

## Suricata feed (services/0010 §1)

`crowdsec_syslog_feeds` opens a syslog datasource per entry (`acquis.d/syslog-<name>.yaml`, RFC5424/TCP); the firewalls ship their syslog (incl. Suricata EVE, `program=suricata`) to it from the catalog (`opn_syslog_destinations`), and `crowdsecurity/suricata` (parser + `suricata-alerts` scenario + context) turns high/major alerts into decisions the OPNsense bouncer enforces. OPNsense sends EVE under program `suricata`, which the hub parser does not match, so a local `s01-parse` node (`crowdsec_suricata_syslog_program`) renames JSON payloads to `suricata-evelogs` before `s01-parse`. Verify: `cscli metrics` (acquisition `syslog-suricata` lines read AND parsed, parser `crowdsecurity/suricata-evelogs` hits), `cscli alerts list --scenario crowdsecurity/suricata-alerts`.
