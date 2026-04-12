#!/usr/bin/env bash
# run-opnsense.sh — wrapper that opens SSH tunnel before running opnsense playbook
# Usage: ./scripts/run-opnsense.sh [ansible-playbook args...]
# Example: ./scripts/run-opnsense.sh --tags firewall
#          ./scripts/run-opnsense.sh --tags firewall --check

set -euo pipefail

PROXMOX_HOST="10.6.224.105"
PROXMOX_PORT="22222"
OPNSENSE_HOST="10.6.224.106"
OPNSENSE_PORT="443"
LOCAL_PORT="8443"
SSH_KEY="${HOME}/.ssh/id_ed25519_rune_automation"

cleanup() {
  echo "[tunnel] Closing SSH tunnel..."
  pkill -f "ssh.*${LOCAL_PORT}:${OPNSENSE_HOST}:${OPNSENSE_PORT}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Kill any stale tunnel
pkill -f "ssh.*${LOCAL_PORT}:${OPNSENSE_HOST}:${OPNSENSE_PORT}" 2>/dev/null || true
sleep 0.3

echo "[tunnel] Opening SSH tunnel localhost:${LOCAL_PORT} → ${OPNSENSE_HOST}:${OPNSENSE_PORT} via ${PROXMOX_HOST}"
ssh -i "${SSH_KEY}" \
    -p "${PROXMOX_PORT}" \
    -o StrictHostKeyChecking=no \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -f -N \
    -L "${LOCAL_PORT}:${OPNSENSE_HOST}:${OPNSENSE_PORT}" \
    "root@${PROXMOX_HOST}"

echo "[tunnel] Waiting for port ${LOCAL_PORT}..."
for i in $(seq 1 10); do
  nc -z 127.0.0.1 "${LOCAL_PORT}" 2>/dev/null && break
  sleep 0.5
done
echo "[tunnel] Port ${LOCAL_PORT} ready."

echo "[ansible] Running playbook..."
ANSIBLE_VAULT_PASSWORD_FILE=".vault_pass" \
ansible-playbook \
  -i inventories/poc/hosts.yml \
  playbooks/opnsense.yml \
  "$@"
