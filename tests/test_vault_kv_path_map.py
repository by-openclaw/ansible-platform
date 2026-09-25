"""Every controller secret file has to resolve to exactly one Vault KV path, and
the map fails closed: an unmapped name aborts the migration rather than guessing.
That refusal is the right behaviour and it is also why one missing name stopped
the whole secrets→Vault migration (#566).

These render the real expression out of playbooks/tasks/vault_kv_path.yml, so a
change to the rules is what the tests see — not a copy of them.
"""

from __future__ import annotations

import pathlib
import re

import pytest

yaml = pytest.importorskip("yaml")
jinja2 = pytest.importorskip("jinja2")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASK = ROOT / "playbooks" / "tasks" / "vault_kv_path.yml"
MAP = ROOT / "playbooks" / "vars" / "vault_kv_map.yml"

EXPLICIT = yaml.safe_load(MAP.read_text())["vault_kv_explicit_map"]


def _expression() -> str:
    """The _kv_rel template, lifted straight out of the task file."""
    doc = yaml.safe_load(TASK.read_text())
    return doc[0]["ansible.builtin.set_fact"]["_kv_rel"]


def resolve(name: str) -> str:
    env = jinja2.Environment()  # noqa: S701 — resolving a path, not rendering HTML
    env.tests["match"] = lambda value, pattern: re.match(pattern, value) is not None
    return env.from_string(_expression()).render(
        _kv_base=name,
        # platform_org appears in one explicit value; its literal does not matter here.
        vault_kv_explicit_map={k: v.replace("{{ platform_org }}", "org") for k, v in EXPLICIT.items()},
    ).strip()


# --- the four that blocked the migration (#566) -------------------------------

@pytest.mark.parametrize(
    "name,expected",
    [
        ("net-opnsense-lab-svc-ansible", "opnsense-lab/svc-ansible"),
        ("net-opnsense-lab-vm-opns-lab-01", "opnsense-lab/vm-opns-lab-01"),
        ("net-opnsense-test-oob-admin", "opnsense-test/oob-admin"),
        ("net-opnsense-test-vm-opns-test-01", "opnsense-test/vm-opns-test-01"),
    ],
)
def test_lab_and_test_firewalls_resolve(name, expected):
    assert resolve(name) == expected


def test_lab_and_test_never_land_in_the_prod_firewall_tree():
    """The whole reason they get their own prefix: a lab credential on the path
    something reads for the prod firewall is the failure this map prevents."""
    for name in ("net-opnsense-lab-svc-ansible", "net-opnsense-test-oob-admin"):
        assert not resolve(name).startswith("opnsense/")


def test_the_prod_firewall_is_unaffected():
    # Explicitly mapped, and the new rule must not shadow it.
    assert resolve("net-opnsense-prod-svc-ansible") == "opnsense/api"
    assert resolve("net-opnsense-prod-oob-admin") == "opnsense/oob-admin"


# --- the rule families keep working ------------------------------------------

@pytest.mark.parametrize(
    "name,expected",
    [
        ("app-oidc-harbor", "harbor/oidc"),
        ("db-pgsql-netbox", "netbox/db-pgsql"),
        ("infra-seaweedfs-mailcow", "mailcow/s3"),
        ("app-smtp-grafana", "grafana/smtp"),
    ],
)
def test_rule_families(name, expected):
    assert resolve(name) == expected


def test_an_explicit_entry_beats_a_rule():
    # db-pgsql-superuser would otherwise become superuser/db-pgsql.
    assert resolve("db-pgsql-superuser") == "postgres/superuser"


def test_an_unknown_name_still_fails_closed():
    assert resolve("something-nobody-mapped") == "__UNMAPPED__"


def test_every_controller_secret_now_resolves():
    """The check that actually answers #566: nothing left blocks the migration."""
    import glob
    import os

    base = os.path.expanduser("~/.openclaw/workspace/infra/secrets")
    files = glob.glob(base + "/fabric/**/*.json", recursive=True) + glob.glob(base + "/shared/*.json")
    if not files:
        pytest.skip("controller secret folder not present (CI)")

    play = yaml.safe_load((ROOT / "playbooks" / "secrets-to-vault.yml").read_text())
    excluded = re.compile("|".join(play[0]["vars"]["secrets_sync_exclude"]))

    unmapped = sorted(
        {
            n
            for n in (os.path.splitext(os.path.basename(f))[0] for f in files)
            if not excluded.search(n) and resolve(n) == "__UNMAPPED__"
        }
    )
    assert not unmapped, f"these would abort secrets-to-vault.yml: {unmapped}"
