"""Every holder of the shared wildcard is re-synced after a renewal.

lego renews the wildcard on the Traefik host; the services that hold a copy (roles that
include `tls_cert`) get the new one only from playbooks/certs-sync.yml, which the controller
runs every week. Until 2026-11-06 three holders had no play there — Vault, the Redis Sentinels
and etcd — so they kept the August certificate while Traefik served the renewed one (found
with 15 days left). A role that installs the wildcard must therefore have a play in
certs-sync.yml, and the task file that play runs must be the one that installs it.
"""

from __future__ import annotations

import pathlib
import re

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROLES = ROOT / "roles"
SYNC = ROOT / "playbooks" / "certs-sync.yml"

TLS_CERT = re.compile(r"^\s*name:\s*tls_cert\s*$", re.MULTILINE)


def _holders() -> dict[str, set[str]]:
    """role -> the task files of that role that include tls_cert."""
    holders: dict[str, set[str]] = {}
    for path in sorted(ROLES.glob("*/tasks/*.yml")):
        role = path.parts[-3]
        if role == "tls_cert":
            continue
        if TLS_CERT.search(path.read_text()):
            holders.setdefault(role, set()).add(path.name)
    return holders


def _synced() -> dict[str, set[str]]:
    """role -> the task files certs-sync.yml runs for it (include_role / import_role)."""
    synced: dict[str, set[str]] = {}
    for play in yaml.safe_load(SYNC.read_text()) or []:
        for task in play.get("tasks", []) or []:
            for key in ("ansible.builtin.include_role", "ansible.builtin.import_role"):
                spec = task.get(key)
                if spec:
                    tasks_from = spec.get("tasks_from", "main.yml")
                    if not tasks_from.endswith(".yml"):
                        tasks_from += ".yml"
                    synced.setdefault(spec["name"], set()).add(tasks_from)
    return synced


def test_the_holders_are_found() -> None:
    # A rename of the role or of the include form would make every other test vacuous.
    assert {"postgresql", "redis", "vault"} <= set(_holders())


@pytest.mark.parametrize("role", sorted(_holders()))
def test_every_holder_has_a_sync_play(role: str) -> None:
    assert role in _synced(), (
        f"roles/{role} installs the wildcard (tls_cert) but playbooks/certs-sync.yml has no play "
        f"for it: after a renewal it keeps serving the old certificate"
    )


@pytest.mark.parametrize("role", sorted(_holders()))
def test_the_sync_play_runs_the_file_that_installs_it(role: str) -> None:
    runs = _synced().get(role, set())
    installs = _holders()[role]
    assert runs & installs, (
        f"certs-sync.yml runs roles/{role} tasks {sorted(runs)}, but the wildcard is installed by "
        f"{sorted(installs)}"
    )


# --- every holder HOST, not only every holder role ------------------------------------------
# The PostgreSQL and Redis plays targeted the groups `postgresql` and `redis` — one member each —
# while the clusters are deployed on `patroni` and `redis_cluster`: the Redis replica kept the
# old certificate. The hosts a sync play reaches must include every host the role is deployed on.

INVENTORY = ROOT / "inventories" / "prod" / "hosts.yml"
GROUPS_DEFAULT = re.compile(r"^\{\{\s*groups\['([\w-]+)'\]\s*\|\s*default\(groups\['[\w-]+'\]\)\s*\}\}$")
TARGET_DEFAULT = re.compile(r"^\{\{\s*target\s*\|\s*default\('([\w:-]+)'\)\s*\}\}$")


def _groups() -> dict[str, set[str]]:
    """group -> hosts, children included, read from the inventory file (no vars, no vault)."""
    direct: dict[str, set[str]] = {}
    children: dict[str, set[str]] = {}

    def walk(name: str, node: dict | None) -> None:
        node = node or {}
        direct.setdefault(name, set()).update((node.get("hosts") or {}).keys())
        for child, sub in (node.get("children") or {}).items():
            children.setdefault(name, set()).add(child)
            walk(child, sub)

    for name, node in (yaml.safe_load(INVENTORY.read_text()) or {}).items():
        walk(name, node)

    def resolve(name: str, seen: frozenset[str] = frozenset()) -> set[str]:
        hosts = set(direct.get(name, set()))
        for child in children.get(name, set()) - seen:
            hosts |= resolve(child, seen | {name})
        return hosts

    return {name: resolve(name) for name in set(direct) | set(children)}


def _hosts(pattern: str) -> set[str]:
    pattern = pattern.strip()
    for form in (GROUPS_DEFAULT, TARGET_DEFAULT):
        match = form.match(pattern)
        if match:
            pattern = match.group(1)
    assert not any(c in pattern for c in "{}&!"), f"unsupported host pattern: {pattern!r}"
    groups = _groups()
    hosts: set[str] = set()
    for part in pattern.split(":"):
        hosts |= groups.get(part, {part})
    return hosts


def _deployed_on(role: str) -> set[str]:
    """Every host a playbook (other than certs-sync.yml) lists the role under `roles:` for."""
    hosts: set[str] = set()
    for path in sorted((ROOT / "playbooks").glob("*.yml")):
        if path == SYNC:
            continue
        for play in yaml.safe_load(path.read_text()) or []:
            if not isinstance(play, dict) or "hosts" not in play:
                continue
            names = [r if isinstance(r, str) else (r.get("role") or r.get("name")) for r in play.get("roles") or []]
            if role in names:
                hosts |= _hosts(play["hosts"])
    return hosts


def _sync_hosts(role: str) -> set[str]:
    hosts: set[str] = set()
    for play in yaml.safe_load(SYNC.read_text()) or []:
        for task in play.get("tasks", []) or []:
            spec = task.get("ansible.builtin.include_role") or task.get("ansible.builtin.import_role")
            if spec and spec.get("name") == role:
                hosts |= _hosts(play["hosts"])
    return hosts


def test_the_inventory_groups_resolve() -> None:
    groups = _groups()
    assert len(groups.get("patroni", set())) == 3, "the PostgreSQL cluster group no longer resolves — test stale"


@pytest.mark.parametrize("role", sorted(_holders()))
def test_the_sync_play_reaches_every_host_the_role_is_deployed_on(role: str) -> None:
    missing = _deployed_on(role) - _sync_hosts(role)
    assert not missing, (
        f"roles/{role} is deployed on {sorted(missing)} but certs-sync.yml does not reach them: "
        f"they keep the old certificate after a renewal"
    )
