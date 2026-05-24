#!/usr/bin/env bash
# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/ansible-platform
#
# LXC validation matrix — runs inside each of the 10 test LXCs via `pct exec`.
# Captures: link/IP config, FW gw v4+v6 ping, DNS via FW Unbound,
# IPv6 default route (proves radvd RA accepted), recent RA capture.
#
# Run on the PVE host (srv-proxmox-poc-01) as root:
#   ssh root@srv-proxmox-poc-01 -p 22222 bash -s < lxc_validate_matrix.sh > /tmp/matrix.out 2>&1
#
# OR copy onto PVE then:
#   sh /tmp/lxc_validate_matrix.sh > /tmp/matrix.out 2>&1
#
# Output is plain text with section banners per LXC; grep for "FAIL" or
# parse the summary at the end.

set -u
LOG=${LOG:-/tmp/lxc_validate.$$.out}
SUMMARY=()

declare -A LXC=(
  [1510]="mgmt 10.11.201.100 fd11:201::100 10.11.201.1 fd11:201::1"
  [1511]="dmz 10.11.202.100 fd11:202::100 10.11.202.1 fd11:202::1"
  [1512]="svc 10.11.203.100 fd11:203::100 10.11.203.1 fd11:203::1"
  [1513]="vpn 10.11.204.100 fd11:204::100 10.11.204.1 fd11:204::1"
  [1514]="iot 10.11.210.100 fd11:210::100 10.11.210.1 fd11:210::1"
  [1515]="voip 10.11.211.100 fd11:211::100 10.11.211.1 fd11:211::1"
  [1516]="storage 10.11.220.100 fd11:220::100 10.11.220.1 fd11:220::1"
  [1517]="media 10.11.230.100 fd11:230::100 10.11.230.1 fd11:230::1"
  [1518]="gaming 10.11.232.100 fd11:232::100 10.11.232.1 fd11:232::1"
  [1519]="cctv 10.11.240.100 fd11:240::100 10.11.240.1 fd11:240::1"
)

run() { pct exec "$1" -- sh -c "$2" 2>&1; }

probe_lxc() {
  local vmid=$1
  local meta="${LXC[$vmid]}"
  local zone v4 v6 gw4 gw6
  read -r zone v4 v6 gw4 gw6 <<<"$meta"
  echo
  echo "========================================================================"
  echo "VMID $vmid  zone=$zone  expected v4=$v4 v6=$v6  gw4=$gw4 gw6=$gw6"
  echo "========================================================================"
  local pass=0 fail=0

  # Check 1: hostname + reachability
  local hn
  hn=$(run "$vmid" "hostname")
  echo "[1/6] hostname: $hn"

  # Check 2: configured IPv4 matches expected
  local cfg4
  cfg4=$(run "$vmid" "ip -4 -o addr show dev eth0 | awk '{print \$4}'")
  if echo "$cfg4" | grep -q "^${v4}/"; then
    echo "[2/6] v4 addr   PASS  $cfg4"; pass=$((pass+1))
  else
    echo "[2/6] v4 addr   FAIL  got '$cfg4' want '$v4/24'"; fail=$((fail+1))
  fi

  # Check 3: configured IPv6 matches expected (static fdXX::100)
  local cfg6
  cfg6=$(run "$vmid" "ip -6 -o addr show dev eth0 scope global | awk '{print \$4}'")
  if echo "$cfg6" | grep -qi "^${v6}/"; then
    echo "[3/6] v6 addr   PASS  $cfg6"; pass=$((pass+1))
  else
    echo "[3/6] v6 addr   FAIL  got '$cfg6' want '$v6/64'"; fail=$((fail+1))
  fi

  # Check 4: ping FW v4 gateway
  if run "$vmid" "ping -c 2 -W 2 $gw4 >/dev/null 2>&1"; then
    echo "[4/6] ping4 gw  PASS  $gw4"; pass=$((pass+1))
  else
    echo "[4/6] ping4 gw  FAIL  $gw4 unreachable"; fail=$((fail+1))
  fi

  # Check 5: ping FW v6 gateway
  if run "$vmid" "ping -c 2 -W 2 $gw6 >/dev/null 2>&1 || ping6 -c 2 -W 2 $gw6 >/dev/null 2>&1"; then
    echo "[5/6] ping6 gw  PASS  $gw6"; pass=$((pass+1))
  else
    echo "[5/6] ping6 gw  FAIL  $gw6 unreachable"; fail=$((fail+1))
  fi

  # Check 6: IPv6 default route via FW link-local (proves radvd RA accepted)
  local v6def
  v6def=$(run "$vmid" "ip -6 route show default 2>/dev/null | head -1")
  if echo "$v6def" | grep -qE "default via fe80::"; then
    echo "[6/6] v6 default route via radvd link-local PASS  $v6def"; pass=$((pass+1))
  else
    echo "[6/6] v6 default route via radvd link-local FAIL  '$v6def' (no fe80:: default seen — radvd RA not accepted yet)"; fail=$((fail+1))
  fi

  # Bonus: DNS via FW Unbound (don't count in PASS/FAIL — informational)
  local dns4 dns6
  dns4=$(run "$vmid" "getent hosts example.com 2>&1 | head -1")
  dns6=$(run "$vmid" "getent ahostsv6 example.com 2>&1 | head -1")
  echo "[BONUS] DNS A    $dns4"
  echo "[BONUS] DNS AAAA $dns6"

  SUMMARY+=("VMID=$vmid  zone=$zone  pass=$pass/6  fail=$fail/6")
}

echo "===== LXC VALIDATION MATRIX — $(date -Is) ====="
echo "Host: $(hostname)  (expect srv-proxmox-poc-01)"
echo
for vmid in "${!LXC[@]}"; do probe_lxc "$vmid"; done | sort -k2 -n
echo
echo "============== SUMMARY =============="
for line in "${SUMMARY[@]}"; do echo "  $line"; done
totalfail=0
for line in "${SUMMARY[@]}"; do
  f=$(echo "$line" | sed -n 's/.*fail=\([0-9]*\).*/\1/p')
  totalfail=$((totalfail + f))
done
echo "============== TOTAL =============="
echo "  Total FAIL across fleet: $totalfail"
[ $totalfail -eq 0 ] && echo "  RESULT: ALL GREEN" || echo "  RESULT: $totalfail check(s) FAIL"
