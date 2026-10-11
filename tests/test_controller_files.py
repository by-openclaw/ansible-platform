"""The controller keeps only the declared credential files (playbooks/controller-files.yml).

The keep-list is data: a pattern that is too wide would silently keep everything, and the one
step that cannot be undone must never ride along with another run.
"""

from __future__ import annotations

import pathlib
import re

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = yaml.safe_load((ROOT / "inventories" / "prod" / "group_vars" / "all" / "controller_files.yml").read_text())
PLAY = yaml.safe_load((ROOT / "playbooks" / "controller-files.yml").read_text())[0]
KEPT = DATA["platform_controller_files_kept"]
KEEP_RE = re.compile("^(" + "|".join(e["path"] for e in KEPT) + ")$")


def _tasks(tasks):
    for t in tasks:
        yield t
        yield from _tasks(t.get("block", []))


def test_every_kept_entry_is_a_pattern_with_its_reader():
    for entry in KEPT:
        re.compile(entry["path"])
        assert len(entry.get("reason", "")) > 10, entry["path"]


@pytest.mark.parametrize(
    "name",
    [
        "vault-init.json",
        "app-vault-approle-ansible-deploy.json",
        "fabric/app-vault-approle-gitlab.json",
        "fabric/os-svc-ansible-prod.json",
        "fabric/net-opnsense-prod-oob-admin.json",
        "fabric/net-opnsense-test-svc-ansible.json",
        "fabric/OPNsense.seed-bootstrap.json",
        "shared/ci-github-rune.json",
        "backups/vault/vault-20261006T075321Z.snap",
        "print-kit/01-vault-unseal-shares.json",
    ],
)
def test_what_a_play_reads_before_vault_is_kept(name):
    assert KEEP_RE.match(name)


@pytest.mark.parametrize(
    "name",
    [
        "fabric/db-pgsql-netbox.json",
        "fabric/app-oidc-harbor.json",
        "fabric/app-vault-seal.json",
        "fabric/net-opnsense-lab-svc-ansible.json",
        "fabric/net-opnsense-prod-svc-ansible.json.485784.2026-10-11@08:41:47~",
        "fabric/OPNsense.seed-bootstrap.json.485910.2026-10-11@08:41:55~",
        "shared/ci-github-opus.json",
        "vault-init.json.pre-revoke.bak",
        "archive/net-opnsense-root-poc.json",
        "_stale/db-pgsql-defguard.json",
        "anything-new.json",
    ],
)
def test_a_copy_of_a_vault_document_or_an_old_file_is_not_kept(name):
    assert not KEEP_RE.match(name)


def test_the_set_aside_area_is_inside_the_folder_and_never_kept():
    aside = DATA["platform_controller_files_set_aside"]
    assert "/" not in aside
    assert not KEEP_RE.match(f"{aside}/fabric/x.json")


def test_files_are_moved_not_deleted():
    block = next(t for t in PLAY["tasks"] if "block" in t)
    assert "controller_files_set_aside" in str(block["when"])
    for t in block["block"]:
        assert "state: absent" not in yaml.safe_dump(t), t["name"]
        cmd = t.get("ansible.builtin.command")
        if cmd:
            assert cmd["argv"][0] in ("mv", "rmdir"), t["name"]
            assert "removes" in cmd, t["name"]


def test_only_the_purge_deletes_and_only_when_asked_alone():
    deleting = [t for t in _tasks(PLAY["tasks"]) if t.get("ansible.builtin.file", {}).get("state") == "absent"]
    assert len(deleting) == 1
    when = " ".join(deleting[0]["when"])
    assert "controller_files_purge | bool" in when
    assert "not (controller_files_set_aside | bool)" in when
    assert PLAY["vars"]["controller_files_purge"] is False
    assert PLAY["vars"]["controller_files_set_aside"] is False
