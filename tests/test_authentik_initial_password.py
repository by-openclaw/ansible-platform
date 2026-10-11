"""A person owns their password (owner, 2026-10-11, option B).

The play sets a password ONCE, when the provider has never recorded one for the account
(`password_change_date` is null). Without that gate every full run re-applied Vault's copy and a
password changed in the UI silently reverted.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASKS = yaml.safe_load((ROOT / "roles" / "authentik" / "tasks" / "blueprints.yml").read_text())


def _password_tasks():
    return [t for t in TASKS if "set_password" in str(t.get("ansible.builtin.uri", {}).get("url", ""))]


def test_exactly_one_task_sets_a_password():
    assert len(_password_tasks()) == 1


def test_it_sets_the_first_password_only():
    task = _password_tasks()[0]
    assert any("password_change_date is none" in str(c) for c in task["when"]), (
        "the set_password task must be gated on the provider never having recorded a password"
    )
