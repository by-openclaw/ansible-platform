<!-- Header: ADR compliance audit record — seaweedfs, 2026-10-02. Instrument:
     docs/audits/adr-compliance-checklist.md (every row). Evidence gathered live on
     lxc-seaweedfs-01 (master/volume/filer/S3 APIs, the backup container's log), Prometheus/Loki
     and the PVE node; the fixes ship in the same PR, applied twice (changed=0). -->

# ADR compliance audit — seaweedfs (2026-10-02)

Method: roles/contract_audit (PASS=10 FAIL=0 SKIP=23) + manual walk on the live guest, the cluster APIs, Prometheus/Loki and the PVE node.

**Service:** `seaweedfs` (`roles/seaweedfs`, `playbooks/seaweedfs.yml`) on `lxc-seaweedfs-01` (ct 550) — the platform's S3 engine (`s3.<domain>`, private, scoped identities per tenant), admin console behind forwardAuth, `4.47`, three containers (server, admin, offsite backup) as the `seaweedfs` account on the host network, `/data` = ZFS dataset (268 GB, 213 GB used), SSE-S3 on, continuous replica to Contabo, 22 buckets.
**Verdicts:** **PASS** · **GAP** · **N/A** · **NOT VERIFIED**; gaps are **FIX** (this PR) · **PLATFORM** · **PROPOSE** · **OWNER**. Host-level rows identical to the previous audits carry the same verdict.

## Summary — gaps ranked

| # | Checks | Finding | Where it is fixed |
|---|---|---|---|
| 1 | SEC-17, SEC-13 | **The console password rides on the admin container's command line** (`-adminPassword=…`): visible in `docker inspect` and in the process list; the audit's own container dump printed it into the session log. SeaweedFS `4.47` takes the value as a flag only (no environment or file form), and a non-loopback bind requires it. | **FIX** — the credential rotated in Vault (new value live after the apply); **PLATFORM** — `/proc` `hidepid=invisible` on every host (the hardening role) so only root sees other users' command lines; **PROPOSE** — upstream flag-from-file/env; audit scripts redact `password=` arguments |
| 2 | INF-35 (saturation) | `/data` at 80 % (199 GB of 250 GB; the ZFS dataset quota) with every bucket growing (PBS datastore, Loki, GitLab, Harbor, mirrors). | **OWNER** — raise the dataset quota / extend the pool; the `SeaweedFSVolumeSlotsLow` rule covers the volume slots, a disk-usage rule for `/data` is a platform item |
| 3 | SEC-21, GIT-05 | Pin `4.47` while `4.48` (2026-09-28) is current. | **FIX** — `4.48` |
| 4 | IDN-17, SVC-37 | No `docs/services/seaweedfs.md`. | **FIX** — this PR |
| 5 | SEC-22 / NAM-01 | Writable rootfs; NetBox empty. | **PLATFORM** |

## Rows

| Area | ID | Verdict | Evidence |
|---|---|---|---|
| naming | NAM-03–08 | PASS | `lxc-seaweedfs-01` → internal A/AAAA + PTR; `s3.<domain>` + `seaweedfs.<domain>` resolve to Traefik inside |
| identity | IDN-01 | PASS | console behind forwardAuth (admin group) + its own login; S3 = scoped machine identities (IAM in the filer), anonymous S3 → 403 |
| identity | IDN-16/17 | PASS / GAP → fixed | console and S3 admin credentials in Vault; service page gap 4 |
| secrets | SEC-01–05, SEC-17 | PASS / **GAP** | `secret/{env}/seaweedfs/{admin, console}`, `offsite/s3`, per-tenant `{svc}/s3` — `vault_secret`, `no_log`; `security.toml` (SSE KEK) 0600; gap 1 for the console flag | <!-- pragma: allowlist secret — names of Vault PATHS, no value -->
| database | SVC-26–29 | N/A | the filer's own store |
| ingress | SVC-01–04, SEC-28, SVC-52/53 | PASS | S3 and console through Traefik (internal-only); master/volume/filer/S3 + gRPC ports admitted from the platform ranges only (ufw, 67 rules); one bucket-set + one identity per tenant; MinIO gone |
| certs | SEC-26 | PASS | TLS at Traefik; gRPC inside the platform ranges |
| mailbox | SVC-16 | N/A | sends no mail |
| decommission | SVC-47 | PASS | catalog row; `seaweedfs_bucket` absent path (archive-before-destroy); the dataset outlives the guest |
| hardening | SEC-15 | PASS | the three containers run as `seaweedfs` (999:991) |
| hardening | SEC-20 | PASS | Lynis hardening index **86** |
| hardening | SEC-21 | **GAP** → fixed | gap 3 |
| hardening | SEC-25, IDN-29 | PASS | sshd `:22222`, no root/password login, fail2ban active |
| logging | INF-27–31 | PASS | three containers journald → promtail → Loki (server 108 lines/h, backup 119) |
| monitoring | INF-33/34, probe | PASS | job `seaweedfs` (`:9327`, 118 families), `node`, `cadvisor`, blackbox `https://s3.<domain>/` up; master leader, 290 volume ids |
| monitoring | INF-35 | GAP (owner/platform) | gap 2 |
| backup | INF-41–43 | PASS | continuous one-way replica to Contabo (`filer.backup`, progressing, 0 errors in 24 h), SSE-S3 (keys in Vault), the node's daily vzdump of the dataset, PBS ct 550 (21 snapshots, config only); pull mirrors (`nextcloud-data`) via `roles/host_job` |
| pins | GIT-01–05 | GAP → fixed | gap 3 |
| contract | SVC-23 | PASS | `check_service_contract.py` 32/32; `contract_audit` PASS=10 FAIL=0 |
