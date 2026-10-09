# The backup liveness signal, in the Prometheus text format (roles/pve_host,
# tasks/backup_signal.yml). Input, slurped in this order: the guests of the cluster,
# the backup jobs, then the backup content of each target storage ($answers documents in all).
#   platform_backup_expected               a guest an enabled job covers, per storage
#   platform_backup_last_timestamp_seconds the start of the newest backup it has there
#   platform_backup_verify_failed          its snapshots whose verification failed
(if length != $answers then error("expected \($answers) answers from PVE, got \(length): a read failed") else . end)
| .[0] as $guests | .[1] as $jobs | (.[2:] | add // []) as $backups
| def ids: (. // "") | tostring | split(",") | map(select(length > 0));
  ($jobs | map(select((.enabled // 1 | tostring) == "1")) | map(
      . as $j | $guests[] | (.vmid | tostring) as $v
      | select(if ($j.all // 0 | tostring) == "1"
               then ($j.exclude | ids | any(. == $v) | not)
               else ($j.vmid | ids | any(. == $v)) end)
      | {storage: $j.storage, vmid: $v, name: (.name // $v)})
   | unique_by([.storage, .vmid])) as $expected
| ($backups | map(select(.vmid != null) | {storage: (.volid | split(":")[0]), vmid: (.vmid | tostring), ctime, verification})
   | group_by([.storage, .vmid])
   | map({storage: .[0].storage, vmid: .[0].vmid, last: (map(.ctime) | max),
          failed: (map(select(.verification.state? == "failed")) | length)})) as $have
| "# HELP platform_backup_expected Guest covered by an enabled backup job, per target storage.",
  "# TYPE platform_backup_expected gauge",
  ($expected[] | "platform_backup_expected{storage=\"\(.storage)\",vmid=\"\(.vmid)\",name=\"\(.name)\"} 1"),
  "# HELP platform_backup_last_timestamp_seconds Start of the newest backup of the guest on the storage.",
  "# TYPE platform_backup_last_timestamp_seconds gauge",
  ($have[] | "platform_backup_last_timestamp_seconds{storage=\"\(.storage)\",vmid=\"\(.vmid)\"} \(.last)"),
  "# HELP platform_backup_verify_failed Snapshots of the guest whose verification failed.",
  "# TYPE platform_backup_verify_failed gauge",
  ($have[] | "platform_backup_verify_failed{storage=\"\(.storage)\",vmid=\"\(.vmid)\"} \(.failed)")
