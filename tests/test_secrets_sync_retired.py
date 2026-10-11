"""A document retired by roles/vault_tidy must stay out of the store.

`secrets-to-vault.yml` writes every document that is absent in Vault when its file
still exists on the controller — which is exactly the state of a retired document.
These check that the write sits behind the retired list, and that the list is the
inventory's.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASKS = ROOT / "playbooks" / "tasks" / "vault_sync_one.yml"
PLAY = ROOT / "playbooks" / "secrets-to-vault.yml"
RETIRED = ROOT / "inventories" / "prod" / "group_vars" / "all" / "vault_retired.yml"
GUARD = "secrets_sync_retired_paths"


def _writes(tasks: list) -> list:
    return [t for t in tasks if t.get("ansible.builtin.uri", {}).get("method") == "POST"]


def test_no_write_outside_the_guarded_block():
    tasks = yaml.safe_load(TASKS.read_text())
    assert not _writes(tasks), "a write to Vault sits outside the retired-document guard"


def test_the_write_is_behind_the_retired_list():
    tasks = yaml.safe_load(TASKS.read_text())
    guarded = [t for t in tasks if "block" in t and _writes(t["block"])]
    assert len(guarded) == 1, "the write task moved — this test is stale"
    assert f"not in {GUARD}" in str(guarded[0]["when"])


def test_the_list_comes_from_the_inventory():
    play = yaml.safe_load(PLAY.read_text())[0]
    assert "platform_vault_retired_paths" in play["vars"][GUARD]
    data = yaml.safe_load(RETIRED.read_text())
    assert "platform_vault_retired_documents" in data["platform_vault_retired_paths"]
    assert "platform_vault_restored_documents" in data["platform_vault_retired_paths"]


def test_a_restored_document_is_not_also_declared_retired():
    data = yaml.safe_load(RETIRED.read_text())
    retired = {d["path"] for d in data["platform_vault_retired_documents"]}
    restored = {d["path"] for d in data["platform_vault_restored_documents"]}
    assert not retired & restored
