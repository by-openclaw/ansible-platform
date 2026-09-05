#!/usr/bin/env python3
"""Reconcile a Discord guild (server) from desired JSON. Idempotent; prints one
line per change and a final JSON line {"changes": N, "webhooks": {name: {"id","url","channel"}}}.
Token via env DISCORD_TOKEN (never printed). Desired: env DISCORD_DESIRED (JSON)."""
import json, os, sys, time, urllib.request, urllib.error

API = "https://discord.com/api/v10"
TOKEN = os.environ["DISCORD_TOKEN"].strip()
D = json.loads(os.environ["DISCORD_DESIRED"])
GID = D["guild_id"]
changes = 0
P = {"VIEW_CHANNEL": 1 << 10, "SEND_MESSAGES": 1 << 11, "READ_MESSAGE_HISTORY": 1 << 16,
     "ADD_REACTIONS": 1 << 6, "MANAGE_MESSAGES": 1 << 13}


def api(method, path, body=None):
    for attempt in range(5):
        req = urllib.request.Request(API + path, method=method,
                                     headers={"Authorization": "Bot " + TOKEN, "Content-Type": "application/json",
                                              "User-Agent": "by-research-chatops/1.0"},
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                t = r.read()
                return json.loads(t) if t else None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", "2")) + 0.5); continue
            raise SystemExit(f"API {method} {path} -> {e.code} {e.read()[:200]!r}")
    raise SystemExit("rate limited too long")


def log(kind, what):
    global changes
    changes += 1
    print(f"{kind} {what}")


guild = api("GET", f"/guilds/{GID}")
everyone_id = GID  # @everyone role id == guild id
roles = {r["name"]: r for r in api("GET", f"/guilds/{GID}/roles")}
me = api("GET", "/users/@me")

# --- roles ------------------------------------------------------------------
for r in D.get("roles", []):
    if r["name"] not in roles:
        roles[r["name"]] = api("POST", f"/guilds/{GID}/roles",
                               {"name": r["name"], "color": r.get("color", 0), "hoist": r.get("hoist", False), "mentionable": True})
        log("role+", r["name"])

# --- categories + channels --------------------------------------------------
chans = api("GET", f"/guilds/{GID}/channels")
by_name_type = {(c["name"], c["type"]): c for c in chans}
bot_role = roles.get(D.get("bot_role", ""))
admin_role = roles.get("platform-admins")


def overwrites_for(ch):
    if not ch.get("announce"):
        return None
    ow = [{"id": everyone_id, "type": 0, "allow": str(P["VIEW_CHANNEL"] | P["READ_MESSAGE_HISTORY"] | P["ADD_REACTIONS"]),
           "deny": str(P["SEND_MESSAGES"])}]
    if admin_role:
        ow.append({"id": admin_role["id"], "type": 0, "allow": str(P["SEND_MESSAGES"] | P["MANAGE_MESSAGES"]), "deny": "0"})
    if bot_role:
        ow.append({"id": bot_role["id"], "type": 0, "allow": str(P["SEND_MESSAGES"] | P["MANAGE_MESSAGES"]), "deny": "0"})
    return ow


def ow_equal(current, wanted):
    cur = {(o["id"], int(o.get("allow", 0)), int(o.get("deny", 0))) for o in (current or [])}
    want = {(o["id"], int(o["allow"]), int(o["deny"])) for o in (wanted or [])}
    return cur == want


created_announce = None
for cat in D.get("categories", []):
    c = by_name_type.get((cat["name"], 4))
    if not c:
        c = api("POST", f"/guilds/{GID}/channels", {"name": cat["name"], "type": 4})
        by_name_type[(cat["name"], 4)] = c
        log("category+", cat["name"])
    for ch in cat.get("channels", []):
        t = by_name_type.get((ch["name"], 0))
        wanted_ow = overwrites_for(ch)
        if not t:
            body = {"name": ch["name"], "type": 0, "parent_id": c["id"], "topic": ch.get("topic", "")}
            if wanted_ow:
                body["permission_overwrites"] = wanted_ow
            t = api("POST", f"/guilds/{GID}/channels", body)
            by_name_type[(ch["name"], 0)] = t
            log("channel+", f"#{ch['name']} ({cat['name']})")
            if ch["name"] == "announcements":
                created_announce = t
        else:
            patch = {}
            if t.get("parent_id") != c["id"]:
                patch["parent_id"] = c["id"]
            if (t.get("topic") or "") != ch.get("topic", ""):
                patch["topic"] = ch.get("topic", "")
            if wanted_ow is not None and not ow_equal(t.get("permission_overwrites"), wanted_ow):
                patch["permission_overwrites"] = wanted_ow
            if patch:
                api("PATCH", f"/channels/{t['id']}", patch)
                log("channel~", f"#{ch['name']} {','.join(patch)}")

# --- webhooks (one per channel that declares one) -----------------------------
existing = {w["name"]: w for w in api("GET", f"/guilds/{GID}/webhooks") if w.get("type") == 1}
out = {}
for cat in D.get("categories", []):
    for ch in cat.get("channels", []):
        name = ch.get("webhook")
        if not name:
            continue
        chan = by_name_type[(ch["name"], 0)]
        w = existing.get(name)
        if w and w.get("channel_id") != chan["id"]:
            api("PATCH", f"/webhooks/{w['id']}", {"channel_id": chan["id"]})
            log("webhook~", f"{name} -> #{ch['name']}")
            w = api("GET", f"/webhooks/{w['id']}")
        if not w:
            w = api("POST", f"/channels/{chan['id']}/webhooks", {"name": name})
            log("webhook+", f"{name} -> #{ch['name']}")
        if not w.get("token"):
            w = api("GET", f"/webhooks/{w['id']}")
        out[name] = {"id": w["id"], "url": f"https://discord.com/api/webhooks/{w['id']}/{w['token']}", "channel": ch["name"]}

if created_announce and D.get("post_ready_message"):
    api("POST", f"/channels/{created_announce['id']}/messages",
        {"content": f"chat-ops online — server managed as code by **{me['username']}** (ansible-platform `discord_guild`)."})
    log("message+", "#announcements ready")

print("DISCORD_DONE changes=%d" % changes)
print(json.dumps({"changes": changes, "webhooks": out}))
