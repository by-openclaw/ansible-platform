#!/usr/bin/env python3
# Copyright (c) 2026 BY-SYSTEMS SRL. MIT License.
# SPDX-License-Identifier: MIT
# Repo: https://github.com/by-openclaw/ansible-platform
"""Provision the OOB break-glass admin on OPNsense via lib-opnsense MVC API.

Group-based access (never per-person privilege): creates an admin group, assigns
the full-GUI `page-all` privilege to the GROUP, then creates the OOB admin user
as a member and mints an API key. Idempotent (lib ensure()): re-runs are noop.

Secrets (WebGUI password + API key/secret) are written 0600 to the infra secret
store and NEVER printed. Dry-run by default; pass --apply to write changes.

    Dry-run:  python3 scripts/opn_oob_admin.py
    Apply:    python3 scripts/opn_oob_admin.py --apply

Reads API credentials from secrets/net-opnsense-<env>-poc.json (same as
fw_apply_direct.py).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import secrets
import string
import sys
from pathlib import Path
from typing import Any

from opnsense.client import OpnsenseClient
from opnsense.exceptions import OpnsenseError
from opnsense.managers.auth.api_key import AuthApiKeyManager
from opnsense.managers.auth.group import AuthGroupManager
from opnsense.managers.auth.priv import AuthPrivManager
from opnsense.managers.auth.user import AuthUserManager

WORKSPACE_SECRETS = Path("/home/by-systems/.openclaw/workspace/infra/secrets")
PRIV_FULL_GUI = "page-all"

log = logging.getLogger("opn_oob_admin")


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def load_credentials(env: str) -> dict[str, Any]:
    path = WORKSPACE_SECRETS / f"net-opnsense-{env}-poc.json"
    if not path.exists():
        raise SystemExit(f"Secret file missing: {path}")
    fields = json.loads(path.read_text()).get("fields", {})
    for k in ("host", "key", "secret"):
        if not fields.get(k):
            raise SystemExit(f"Secret file missing field 'fields.{k}'")
    return {
        "host": fields["host"],
        "port": int(fields.get("port") or 443),
        "key": fields["key"],
        "secret": fields["secret"],
        "verify_ssl": _as_bool(fields.get("verify_ssl", False)),
    }


def gen_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def resolve_gid(groups: AuthGroupManager, name: str) -> str | None:
    for row in await groups.list():
        if row.get("name") == name:
            return row.get("gid")
    return None


async def provision(args: argparse.Namespace) -> int:
    creds = load_credentials(args.env)
    user = args.user
    group = args.group
    email = f"{user}@{args.domain}"
    check = not args.apply

    async with OpnsenseClient(
        host=creds["host"], port=creds["port"], key=creds["key"],
        secret=creds["secret"], verify_ssl=creds["verify_ssl"],
    ) as c:
        groups = AuthGroupManager(c)
        users = AuthUserManager(c)
        priv = AuthPrivManager(c)
        keys = AuthApiKeyManager(c)

        mode = "DRY-RUN (no changes)" if check else "APPLY (live changes)"
        log.info("Mode: %s | host=%s user=%s group=%s", mode, creds["host"], user, group)

        # 1. Group
        r = await groups.ensure("present", {"name": group,
                                            "description": "OOB break-glass administrators"},
                                check_mode=check)
        log.info("[group] %-8s changed=%s", r.action, r.changed)

        # gid is needed for user membership; resolve live (exists already, or just created)
        gid = await resolve_gid(groups, group)
        if not check and gid is None:
            raise SystemExit("group gid unresolved after create — aborting")
        log.info("[group] %s gid=%s", group, gid)

        # 2. page-all -> GROUP (group-based access, never per-person)
        r = await priv.ensure(PRIV_FULL_GUI, "group", group, "present", check_mode=check)
        log.info("[priv ] %-8s changed=%s (%s -> group %s)", r.action, r.changed,
                 PRIV_FULL_GUI, group)

        # 3. User as member of the group
        existing = await users.list()
        user_exists = any(u.get("name") == user for u in existing)
        webgui_password = None
        user_params: dict[str, Any] = {
            "name": user,
            "email": email,
            "comment": "OOB break-glass admin (managed by opn_oob_admin.py)",
            "shell": "",
        }
        if gid:
            user_params["group_memberships"] = gid
        if not user_exists:
            webgui_password = gen_password()
            user_params["password"] = webgui_password
        r = await users.ensure("present", user_params, check_mode=check)
        log.info("[user ] %-8s changed=%s (%s, member of %s)", r.action, r.changed,
                 user, group)
        if user_exists:
            log.info("[user ] %s already exists — WebGUI password NOT rotated "
                     "(delete+rerun or set manually to rotate)", user)

        # 4. API key — only if the user has none yet
        existing_keys = await keys.list_keys(username=user)
        api_key = api_secret = None
        if existing_keys:
            log.info("[apikey] user %s already has %d key(s) — not minting another",
                     user, len(existing_keys))
        elif check:
            log.info("[apikey] would mint a new API key for %s", user)
        else:
            kr = await keys.create_key(user)
            api_key = kr.after.get("key")
            api_secret = kr.after.get("secret")
            log.info("[apikey] minted new key for %s", user)

        # 5. Persist secrets (0600) — never printed
        if not check and (webgui_password or api_key):
            out = WORKSPACE_SECRETS / f"net-opnsense-{args.env}-{user}.json"
            payload: dict[str, Any] = {"fields": {
                "host": creds["host"], "port": creds["port"],
                "verify_ssl": creds["verify_ssl"],
                "username": user, "email": email, "group": group,
                "role": "oob-break-glass-admin", "domain": args.domain,
            }}
            # Merge with any existing file so a re-run that only mints a key keeps the pw.
            if out.exists():
                payload["fields"].update(json.loads(out.read_text()).get("fields", {}))
            if webgui_password:
                payload["fields"]["webgui_password"] = webgui_password
            if api_key:
                payload["fields"]["key"] = api_key
                payload["fields"]["secret"] = api_secret
            out.write_text(json.dumps(payload, indent=2))
            out.chmod(0o600)
            log.info("[secret] wrote %s (0600) — credentials NOT shown in terminal", out)

        log.info("Done (%s).", mode)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Provision OPNsense OOB break-glass admin")
    p.add_argument("--env", default="prod")
    p.add_argument("--user", default="oob-admin")
    p.add_argument("--group", default="oob-admins")
    p.add_argument("--domain", default="by-research.be")
    p.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S",
    )
    try:
        return asyncio.run(provision(args))
    except (OpnsenseError, SystemExit) as exc:
        log.error("Failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
