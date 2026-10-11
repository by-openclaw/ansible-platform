"""Who may sign in to Vault (security/0001 §People reading in Vault).

The sign-in application is bound to ONE group at the identity provider, the access group. On a
fresh installation that binding is the only door: an administrator of Vault who is not also in
the access group could not sign in at all.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALL = ROOT / "inventories" / "prod" / "group_vars" / "all"
GROUPS = yaml.safe_load((ALL / "identity.yml").read_text())["platform_service_groups"]["vault"]
PEOPLE = yaml.safe_load((ALL / "people.yml").read_text())["platform_people"]
SSO = (ALL / "sso.yml").read_text()


def test_vault_has_an_access_group_and_an_administrators_group():
    assert GROUPS["access"] and GROUPS["admin"] and GROUPS["access"] != GROUPS["admin"]


def test_the_sign_in_application_is_bound_to_the_access_group():
    app = SSO[SSO.index("- slug: vault\n"):SSO.index("- slug: headlamp\n")]
    assert "platform_service_groups.vault.access" in app
    assert "restrict_to_group: true" in app


def test_every_administrator_of_vault_can_sign_in():
    for person in PEOPLE:
        if GROUPS["admin"] in person["groups"]:
            assert GROUPS["access"] in person["groups"], "a Vault administrator outside the access group cannot sign in"


def test_a_person_with_managed_keys_can_read_them():
    """roles/identity_keys keeps a person's key pair in their area: they must be able to sign in to read it."""
    for person in PEOPLE:
        if person.get("manage_keys"):
            assert GROUPS["access"] in person["groups"]
