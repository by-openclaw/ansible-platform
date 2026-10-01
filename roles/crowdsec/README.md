# role: crowdsec (LAPI)

CrowdSec central LAPI on `lxc-crowdsec-01` (`:8080`, AppSec `:7422` when enabled, Suricata syslog feed `:1515/udp`), **a container**: the pinned vendor image `crowdsecurity/crowdsec:<crowdsec_version>-debian` on the host network. Agents everywhere via `crowdsec_agent`; bouncers on OPNsense (FW) + Traefik (L7 plugin). IPS = CrowdSec (+ Suricata WAN feed).

- **Config ownership:** the vendor entrypoint keeps `config.yaml`; the platform's settings (listen address, agent auto-registration, logs to stdout) live in `config.yaml.local`, which CrowdSec merges over it. Acquisitions and local parsers are written by this role before the container starts.
- **State on the host:** `/etc/crowdsec` (hub, acquisitions, machine + CAPI credentials) and `/var/lib/crowdsec/data` (sqlite: machines, bouncers, decisions) are bind-mounted, so registrations survive a container recreate. `/var/log` and the journal are mounted read-only for the host's own logs (`crowdsec_host_acquisitions`).
- **cscli:** `docker exec crowdsec cscli …` — every role that calls it uses `crowdsec_cscli` (`group_vars/all/crowdsec.yml`).
- **Bouncers:** key in Vault first (get-or-create), registered on the LAPI under that key — a rebuilt LAPI takes back the keys the bouncers already hold.
- **Logs:** the container's stdout → journald → Loki.
- Enrolment gotcha: `lapi status` rc=0 can be a false positive; a rebuilt host leaves a stale machine — delete before re-enrol.

Run: `ansible-playbook -i inventories/prod/hosts.yml playbooks/crowdsec.yml`

## Backup & restore

Class **A**: sqlite (machines/bouncers) in PBS; decisions are ephemeral. Full matrix + drills: [`docs/backup.md`](../../docs/backup.md).

## Runbook

- Health: `docker exec crowdsec cscli machines list` (all validated, fresh heartbeats), `… cscli bouncers list` (recent `last_pull`), `… cscli decisions list`; `docker logs crowdsec`.
- Common: bouncer not pulling → API key mismatch (`fabric/app-crowdsec-bouncer-*.json`).

## Suricata feed (services/0010 §1)

`crowdsec_syslog_feeds` opens a syslog datasource per entry (`acquis.d/syslog-<name>.yaml`, RFC5424/UDP); the firewalls ship their syslog (incl. Suricata EVE, `program=suricata`) to it from the catalog (`opn_syslog_destinations`), and `crowdsecurity/suricata` (parser + `suricata-alerts` scenario + context) turns high/major alerts into decisions the OPNsense bouncer enforces. OPNsense sends EVE under program `suricata`, which the hub parser does not match, so a local `s01-parse` node (`crowdsec_suricata_syslog_program`) renames JSON payloads to `suricata-evelogs` before `s01-parse`. Verify: `cscli metrics` (acquisition `syslog-suricata` lines read AND parsed, parser `crowdsecurity/suricata-evelogs` hits), `cscli alerts list --scenario crowdsecurity/suricata-alerts`.
