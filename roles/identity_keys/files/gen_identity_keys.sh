#!/usr/bin/env bash
# Generate a per-identity ed25519 SSH keypair + an ed25519 GPG key, both passphrase-
# protected, and print ONE JSON object with public+private+passphrase+fingerprints.
# Private material exists only in a transient GNUPGHOME/workdir (caller shreds it)
# and in Vault. Inputs via env: KUSER, KNAME, KEMAIL, SSH_PASS, GPG_PASS.
set -euo pipefail
SSH_PASS="$(openssl rand -base64 32 | tr -dc "A-Za-z0-9" | head -c 40)"
GPG_PASS="$(openssl rand -base64 32 | tr -dc "A-Za-z0-9" | head -c 40)"
WD="$(mktemp -d)"; export GNUPGHOME="$WD/gnupg"; mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"
trap 'find "$WD" -type f -exec shred -u {} + 2>/dev/null; rm -rf "$WD"' EXIT

# --- SSH ---
ssh-keygen -t ed25519 -a 100 -N "$SSH_PASS" -C "${KUSER}@${KEMAIL#*@}" -f "$WD/id" -q
SSH_PRIV="$(cat "$WD/id")"; SSH_PUB="$(cat "$WD/id.pub")"
SSH_FP="$(ssh-keygen -lf "$WD/id.pub" | awk '{print $2}')"

# --- GPG (ed25519 sign+cert, no expiry; loopback pinentry) ---
cat > "$WD/params" <<EOF
%echo generating
Key-Type: eddsa
Key-Curve: ed25519
Key-Usage: sign,cert
Name-Real: $KNAME
Name-Email: $KEMAIL
Expire-Date: 0
Passphrase: $GPG_PASS
%commit
EOF
gpg --batch --pinentry-mode loopback --gen-key "$WD/params" >/dev/null 2>&1
GPG_FP="$(gpg --batch --with-colons --list-keys "$KEMAIL" | awk -F: '/^fpr:/{print $10; exit}')"
GPG_PUB="$(gpg --batch --armor --export "$KEMAIL")"
GPG_PRIV="$(gpg --batch --pinentry-mode loopback --passphrase "$GPG_PASS" --armor --export-secret-keys "$KEMAIL")"

SSH_PASS="$SSH_PASS" GPG_PASS="$GPG_PASS" python3 - "$SSH_PRIV" "$SSH_PUB" "$SSH_FP" "$GPG_PUB" "$GPG_PRIV" "$GPG_FP" <<'PY'
import json,sys,os
sp,pu,fp,gpub,gpriv,gfp=sys.argv[1:7]
print(json.dumps({"ssh_private_key":sp,"ssh_public_key":pu,"ssh_fingerprint":fp,
                  "ssh_passphrase":os.environ["SSH_PASS"],
                  "gpg_public_key":gpub,"gpg_private_key":gpriv,"gpg_fingerprint":gfp,
                  "gpg_passphrase":os.environ["GPG_PASS"]}))
PY
