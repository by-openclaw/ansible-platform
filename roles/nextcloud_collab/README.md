# role: nextcloud_collab

The Nextcloud Talk High-Performance Backend (signaling + Janus SFU + eturnal TURN, image `nextcloud-releases/aio-talk`), the Talk recording server (`aio-talk-recording`) and the Whiteboard server (`nextcloud-releases/whiteboard`) — Docker-in-LXC on `lxc-collab-01` (SVC), all pinned (#396 phase 2). Turns Talk from a 1:1 peer-to-peer tool into a Teams-like meeting service (group calls, screen share, recording) and gives the whiteboard app a real-time backend.

## Contract map

| Concern | How |
|---|---|
| Image pins | `nextcloud_collab_talk_image`, `_recording_image`, `_whiteboard_image` — date/semver tags, never `:latest`. |
| Ingress (HTTP) | three Traefik **path routes under the Nextcloud host name** (`traefik_route` with `path_prefix` + `strip_prefix`): `/standalone-signaling` → 8081, `/recording` → 1234, `/whiteboard` → 3002. Public, rate-limited, no forwardAuth (the backends check their own secrets/JWT). FW rule `PASS DMZ Traefik→SVC collab`. |
| Ingress (TURN) | eturnal listens on 3478 tcp+udp in the container (published on every host address). Both WANs DNAT public **3479** → 3478 (3478 belongs to NetBird's coturn). `talk.<domain>` is public-only DNS (no split-DNS: TURN must resolve to the WAN address). The relay port range is **not** exposed on purpose: browsers only use the TURN channel and the relay peer is the co-located Janus (Nextcloud AIO pattern), so the relay never leaves the container. |
| Secrets | `turn_secret`, `signaling_secret`, `internal_secret`, `recording_secret`, `whiteboard_jwt` get-or-created in Vault `prod/collab/secrets`; env files root 0600 in `/opt/collab`. `roles/nextcloud/tasks/collab.yml` reads the same path for the occ side. | <!-- pragma: allowlist secret -->
| SSO | none of its own — the browsers arrive from a Nextcloud session (signaling tickets, whiteboard JWT). |
| Compose | Debian standalone `docker-compose` (Compose v2). |
| Logging | Docker → journald → promtail → Loki (INF-27). |

## Run

```
ansible-playbook -i inventories/prod/hosts.yml playbooks/collab.yml
```

## Backup & restore

Class **D** (code) — stateless: rooms/chat live in Nextcloud's database, recordings are uploaded into the owner's Nextcloud files when a recording stops. Redeploy the play; secrets come back from Vault. The LXC itself is in the PBS guest jobs (class A).

## Runbook

- Health: `curl -s http://<svc ip>:8081/api/v1/welcome` (signaling), `:1234/api/v1/welcome` (recording), `:3002/` (whiteboard). From the internet: `https://nextcloud.<domain>/standalone-signaling/api/v1/welcome` must answer JSON.
- Nextcloud Settings → Talk shows the HPB as OK once `occ talk:signaling:add … --verify` passed; TURN can be tested from the same page ("Test this server").
- Calls connect on the LAN but not from outside → TURN: FW DNAT `3479`, `talk.<domain>` must resolve to the WAN address (not through the split-DNS), `TURN_SECRET` identical in Vault and Nextcloud.
- Recording button greyed out → `spreed recording_servers` not set, or the recording container cannot reach `https://nextcloud.<domain>/standalone-signaling/` (check its logs).
- Bump versions: change the three image vars → run the play.
