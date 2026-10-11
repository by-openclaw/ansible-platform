"""A document a role reads through a path BUILT FROM A NAME must never be declared retired.

roles/authentik reads one sign-in document per person of the inventory (a convention, not a
list). On 2026-10-11 one of these was archived as "read by nothing": the search for readers
looked for literal paths, and the role's play failed at its secrets step. The documents now sit
in each person's own area, `users/<username>/sign-in`.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALL = ROOT / "inventories" / "prod" / "group_vars" / "all"
RETIRED = yaml.safe_load((ALL / "vault_retired.yml").read_text())
PEOPLE = yaml.safe_load((ALL / "people.yml").read_text())["platform_people"]
RETIRED_PATHS = {d["path"] for d in RETIRED["platform_vault_retired_documents"]}


def test_the_role_still_builds_the_path_this_way():
    defaults = (ROOT / "roles" / "authentik" / "defaults" / "main.yml").read_text()
    assert "~ '/' ~ p.username ~ '/sign-in'" in defaults, (
        "roles/authentik builds its per-person path differently now — adapt this test"
    )


def test_no_person_of_the_inventory_has_their_sign_in_document_retired():
    for person in PEOPLE:
        path = f"users/{person['username']}/sign-in"
        assert path not in RETIRED_PATHS, f"{path} is read by roles/authentik for a person of the inventory"


def test_nothing_of_a_persons_area_is_retired_while_the_person_exists():
    for person in PEOPLE:
        mine = [p for p in RETIRED_PATHS if p.startswith(f"users/{person['username']}/")]
        assert not mine, mine
