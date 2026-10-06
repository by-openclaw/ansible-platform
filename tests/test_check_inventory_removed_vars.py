"""The inventory guard stops a change that removes an inventory variable code still reads: the
variable would fall back to a role default without a word (2026-10-05: the mirror list was deleted
by an unrelated edit and the role configured no mirror from then on).

Each test states the rule in its name, so a failure says which rule broke.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard = _load("check_inventory_removed_vars")

INV = "inventories/prod/group_vars/all/store.yml"
BEFORE = {INV: "store_port: 8333\nstore_mirrors:\n  - name: files\n"}


def _repo(tmp_path: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / "roles").mkdir(exist_ok=True)
    (tmp_path / "playbooks").mkdir(exist_ok=True)
    return tmp_path


def test_a_removed_variable_a_role_still_reads_is_reported(tmp_path):
    root = _repo(tmp_path, {"roles/store/tasks/main.yml": "- debug:\n    msg: '{{ store_mirrors | length }}'\n"})
    problems = guard.check(BEFORE, {INV: "store_port: 8333\n"}, root, {})
    assert len(problems) == 1
    assert "store_mirrors (inventory prod)" in problems[0]
    assert "roles/store/tasks/main.yml" in problems[0]


def test_a_role_default_of_the_same_name_counts_as_a_reader(tmp_path):
    # the silent case: the role keeps working, with its empty default
    root = _repo(tmp_path, {"roles/store/defaults/main.yml": "store_mirrors: []\n"})
    assert guard.check(BEFORE, {INV: "store_port: 8333\n"}, root, {})


def test_a_removed_variable_nothing_reads_is_accepted(tmp_path):
    root = _repo(tmp_path, {"roles/store/tasks/main.yml": "- debug:\n    msg: '{{ store_port }}'\n"})
    assert guard.check(BEFORE, {INV: "store_port: 8333\n"}, root, {}) == []


def test_a_longer_name_is_not_a_reader(tmp_path):
    root = _repo(tmp_path, {"roles/store/tasks/main.yml": "- debug:\n    msg: '{{ store_mirrors_extra }} {{ old_store_mirrors }}'\n"})
    assert guard.check(BEFORE, {INV: "store_port: 8333\n"}, root, {}) == []


def test_a_readme_that_names_the_variable_is_not_a_reader(tmp_path):
    root = _repo(tmp_path, {"roles/store/README.md": "Set `store_mirrors` in the inventory.\n"})
    assert guard.check(BEFORE, {INV: "store_port: 8333\n"}, root, {}) == []


def test_a_variable_moved_to_another_file_of_the_same_inventory_is_not_removed(tmp_path):
    root = _repo(tmp_path, {"roles/store/defaults/main.yml": "store_mirrors: []\n"})
    now = {INV: "store_port: 8333\n", "inventories/prod/group_vars/store/mirrors.yml": "store_mirrors: []\n"}
    assert guard.check(BEFORE, now, root, {}) == []


def test_a_variable_kept_in_another_inventory_only_is_still_removed_from_this_one(tmp_path):
    root = _repo(tmp_path, {"roles/store/defaults/main.yml": "store_mirrors: []\n"})
    now = {INV: "store_port: 8333\n", "inventories/test/group_vars/all/store.yml": "store_mirrors: []\n"}
    problems = guard.check(BEFORE, now, root, {})
    assert len(problems) == 1 and "inventory prod" in problems[0]


def test_a_listed_removal_is_accepted(tmp_path):
    root = _repo(tmp_path, {"roles/store/defaults/main.yml": "store_mirrors: []\n"})
    assert guard.check(BEFORE, {INV: "store_port: 8333\n"}, root, {"store_mirrors": "the default is right"}) == []


def test_an_added_variable_is_not_a_removal(tmp_path):
    root = _repo(tmp_path, {})
    assert guard.check(BEFORE, {INV: BEFORE[INV] + "store_new: 1\n"}, root, {}) == []


def test_an_encrypted_or_tagged_file_is_read_without_error():
    assert guard.names_in("$ANSIBLE_VAULT;1.1;AES256\n6162\n") == set()
    assert guard.names_in("token: !vault |\n  $ANSIBLE_VAULT;1.1;AES256\n  6162\nplain: 1\n") == {"token", "plain"}
    assert guard.names_in("- a\n- b\n") == set()


def test_files_outside_group_and_host_vars_are_ignored():
    files = {"inventories/prod/hosts.yml": "all: {}\n", "inventories/prod/host_vars/h1.yml": "h_var: 1\n", "roles/x/defaults/main.yml": "r: 1\n"}
    assert guard.names_by_env(files) == {"prod": {"h_var"}}
