"""Who holds which group (inventories/prod/group_vars/all/people.yml).

Two rules, both about a service's administrators' group:
- it is held by an ADMIN identity only (`adm_<name>`, naming/0002): the group opens the service's
  administrator login in Vault (security/0001), which a daily account must never read;
- whoever holds it also holds the service's access group, when the service has one: on a fresh
  installation the sign-in application is bound to the access group alone.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALL = ROOT / "inventories" / "prod" / "group_vars" / "all"
IDENTITY = yaml.safe_load((ALL / "identity.yml").read_text())
SERVICE_GROUPS = IDENTITY["platform_service_groups"]
PEOPLE = yaml.safe_load((ALL / "people.yml").read_text())["platform_people"]
ADMIN_GROUPS = {g["admin"] for g in SERVICE_GROUPS.values() if "admin" in g}
PRIVILEGED = ADMIN_GROUPS | {IDENTITY["platform_admins_group"], IDENTITY["platform_infra_admins_group"]}


def test_an_administrators_group_is_held_by_an_admin_identity_only():
    for person in PEOPLE:
        held = sorted(set(person["groups"]) & PRIVILEGED)
        if held:
            assert person["username"].startswith("adm_"), (
                f"a daily account holds {held}: a service's administrator login would be readable by it"
            )


def test_an_administrator_of_a_service_can_sign_in_to_it():
    for service, groups in SERVICE_GROUPS.items():
        if "admin" in groups and "access" in groups:
            for person in PEOPLE:
                if groups["admin"] in person["groups"]:
                    assert groups["access"] in person["groups"], f"{service}: an administrator outside its access group"


def test_every_service_login_has_an_administrators_group_to_read_it():
    for service in IDENTITY["platform_service_logins"]:
        assert "admin" in SERVICE_GROUPS[service], service


def test_the_identity_providers_administrators_are_the_platform_administrators():
    """The map names the group literally (no template in it): it must be the one group."""
    for service in ("authentik", "mailcow"):
        if service in SERVICE_GROUPS and "admin" in SERVICE_GROUPS[service]:
            assert SERVICE_GROUPS[service]["admin"] == IDENTITY["platform_admins_group"]
