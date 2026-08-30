# Archive named Vault KV v2 secrets under secret/fabric/<name> -> secret/fabric/archive/<name>
# (copy, verify, then delete the original). Idempotent: a name already absent from the
# active path is reported "absent" and skipped. Token read from /tmp/.vt. Names via argv.
import urllib.request, json, ssl, sys

TOKEN = open("/tmp/.vt").read().strip()
BASE = "https://127.0.0.1:8200/v1/secret"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE


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
    cur = req("GET", f"/data/fabric/{name}")
    if not cur:
        print(f"  {name}: absent (skip)")
        continue
    data = cur["data"]["data"]
    req("POST", f"/data/fabric/archive/{name}", {"data": data})
    chk = req("GET", f"/data/fabric/archive/{name}")
    if not chk or chk["data"]["data"] != data:
        print(f"  {name}: ARCHIVE-VERIFY-FAILED (original kept)")
        continue
    req("DELETE", f"/metadata/fabric/{name}")   # safe: verified copy in archive/
    changed += 1
    print(f"  {name}: archived+removed")

print(f"CHANGED={changed}")
