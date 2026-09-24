"""The literal guard runs on every commit. An unproven gate is worse than none:
it is trusted without ever being shown to work, which is how four services ended
up with access groups that existed nowhere in code.

Each test states the rule in its name, so a failure says which rule broke.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard = _load("check_platform_literals")


def _hits(text: str) -> set[str]:
    """Every pattern name that matches, comments excluded the way the guard does."""
    found = set()
    for line in text.splitlines():
        code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
        if not code.strip():
            continue
        for label, pattern in guard.PATTERNS.items():
            if pattern.search(code):
                found.add(label)
    return found


class TestTheDomainIsNeverTyped:
    def test_the_domain_literal_is_caught(self):
        assert "domain literal" in _hits('url: "https://x.by-research.be"')

    def test_the_variable_is_allowed(self):
        assert _hits('url: "https://x.{{ platform_domain }}"') == set()

    def test_a_fallback_to_the_literal_is_caught(self):
        # the sneakiest form: looks parameterised, behaves hardcoded
        assert "identity fallback" in _hits("d: \"{{ platform_domain | default('by-research.be') }}\"")


class TestHostAddressesComeFromTheInventory:
    def test_a_host_v6_literal_is_caught(self):
        assert "host IPv6 literal" in _hits('listen: "fd01:3::110"')

    def test_deriving_from_the_inventory_is_allowed(self):
        assert _hits('listen: "{{ hostvars[inventory_hostname].platform_host_v6 }}"') == set()

    def test_a_zone_prefix_is_caught_separately_from_a_host_address(self):
        assert "zone or aggregate CIDR" in _hits('net: "fd01:3::/64"')


class TestAccessGroupsComeFromTheCatalog:
    def test_an_identity_provider_group_literal_is_caught(self):
        assert "access group literal" in _hits('group: "harbor-admins"')

    def test_reading_it_from_the_catalog_is_allowed(self):
        assert _hits('group: "{{ platform_service_groups.harbor.admin }}"') == set()

    def test_the_jumpserver_internal_group_is_not_flagged(self):
        # bastion-admins lives inside JumpServer, not the identity provider. A blanket
        # *-admins rule would flag it and teach people to ignore the guard.
        assert _hits('jumpserver_bastion_group: "bastion-admins"') == set()


class TestCommentsAreNotCode:
    @pytest.mark.parametrize(
        "line",
        [
            "# the old address was fd01:3::110",
            "  # harbor-admins used to be typed here",
            'port: 8080  # by-research.be in a trailing comment',
        ],
    )
    def test_a_literal_in_a_comment_is_ignored(self, line):
        assert _hits(line) == set()


class TestTheGuardRunsOverTheRealTree:
    def test_the_repository_is_clean(self):
        """The tree this test ships with must pass its own guard."""
        assert guard.main() == 0
