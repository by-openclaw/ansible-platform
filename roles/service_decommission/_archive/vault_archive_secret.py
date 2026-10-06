# Archive Vault KV v2 secrets (copy, verify, then delete the original). Two forms per argv:
#   <name>             legacy fabric layout: secret/fabric/<name> -> secret/fabric/archive/<name>
#   <env>/<svc>/<key>  a KV path (has a "/"): secret/<path>       -> secret/archive/<path>
# Idempotent: a secret already absent from the active path is reported "absent" and skipped.
# Token read from /tmp/.vt; VAULT_ADDR from the environment (the task sets it).
import urllib.request, json, ssl, sys

TOKEN = open("/tmp/.vt").read().strip()
import os
BASE = os.environ["VAULT_ADDR"] + "/v1/secret"   # set by the task (platform_vault_addr)
ctx = ssl.create_default_context()   # verified TLS — skip-verify banned


def req(method, path, data=None):
    r = urllib.request.Request(BASE + path, method=method, headers={"X-Vault-Token": TOKEN})
    if data is not None:
        r.data = json.dumps(data).encode(); r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, context=ctx) as resp:
            return json.load(resp) if resp.length != 0 else {}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


changed = 0
for name in sys.argv[1:]:
    src, dst = (name, f"archive/{name}") if "/" in name else (f"fabric/{name}", f"fabric/archive/{name}")
    cur = req("GET", f"/data/{src}")
    if not cur:
        print(f"  {name}: absent (skip)")
        continue
    data = cur["data"]["data"]
    req("POST", f"/data/{dst}", {"data": data})
    chk = req("GET", f"/data/{dst}")
    if not chk or chk["data"]["data"] != data:
        print(f"  {name}: ARCHIVE-VERIFY-FAILED (original kept)")
        continue
    req("DELETE", f"/metadata/{src}")   # safe: verified copy in archive/
    changed += 1
    print(f"  {name}: archived+removed")

print(f"CHANGED={changed}")
