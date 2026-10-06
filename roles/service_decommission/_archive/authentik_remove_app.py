# Remove an Authentik OIDC application, its backing provider, and (optionally) a
# named group — by slug. Idempotent: anything already absent is skipped. Runs
# INSIDE the authentik-server container (reads AUTHENTIK_BOOTSTRAP_TOKEN from env).
# Args: <app-slug> [group-name]
import os, sys, json, urllib.request

TOK = os.environ["AUTHENTIK_BOOTSTRAP_TOKEN"]
BASE = "http://localhost:9000/api/v3"
H = {"Authorization": "Bearer " + TOK}


def call(method, path):
    r = urllib.request.Request(BASE + path, method=method, headers=H)
    try:
        with urllib.request.urlopen(r) as resp:
            body = resp.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


slug = sys.argv[1]
group = sys.argv[2] if len(sys.argv) > 2 else None
changed = 0

apps = (call("GET", f"/core/applications/?slug={slug}") or {}).get("results", [])
for a in apps:
    prov = a.get("provider")
    call("DELETE", f"/core/applications/{a['pk']}/")
    changed += 1
    print(f"  app {slug}: deleted")
    if prov:
        call("DELETE", f"/providers/oauth2/{prov}/")
        print(f"  provider {prov}: deleted")
if not apps:
    print(f"  app {slug}: absent (skip)")

if group:
    grps = (call("GET", f"/core/groups/?name={group}") or {}).get("results", [])
    for g in grps:
        if g["name"] == group:
            call("DELETE", f"/core/groups/{g['pk']}/")
            changed += 1
            print(f"  group {group}: deleted")
    if not grps:
        print(f"  group {group}: absent (skip)")

print(f"CHANGED={changed}")
