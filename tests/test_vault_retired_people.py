"""A document a role reads through a path BUILT FROM A NAME must never be declared retired.

roles/authentik reads `authentik/user-<username>` for every person of the inventory (a
convention, not a list). On 2026-10-11 one of these was archived as "read by nothing": the
search for readers looked for literal paths, and the role's play failed at its secrets step.
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
    assert "'/authentik/user-' ~ (p.username | replace('_', '-'))" in defaults, (
        "roles/authentik builds its per-person path differently now — adapt this test"
    )


def test_no_person_of_the_inventory_has_their_sign_in_document_retired():
    for person in PEOPLE:
        path = "authentik/user-" + person["username"].replace("_", "-")
        assert path not in RETIRED_PATHS, f"{path} is read by roles/authentik for a person of the inventory"
