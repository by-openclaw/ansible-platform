"""Vault held a dead PBS backup token for three weeks (#570): the backup user was
renamed, the controller file was regenerated with the new auth-id, and Vault kept
`pve-backup@pbs!pve` — an auth-id PBS no longer has. Nothing noticed, because the
play consulted the file and a non-empty Vault entry looks held.

So "held" cannot mean "a value is present". It has to mean "a value is present
AND its auth-id is the one we configure". This renders the real condition out of
playbooks/pbs-pve-storage.yml.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")
jinja2 = pytest.importorskip("jinja2")

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAY = ROOT / "playbooks" / "pbs-pve-storage.yml"

USER = "svc-pbs-backup-prod@pbs"
TOKEN = "pve"
LIVE = f"{USER}!{TOKEN}"
OLD = "pve-backup@pbs!pve"   # what Vault actually held


def _condition() -> str:
    for play in yaml.safe_load(PLAY.read_text()):
        for task in play.get("tasks", []):
            fact = task.get("ansible.builtin.set_fact", {})
            if "pbs_tok_held" in fact:
                return fact["pbs_tok_held"]
    raise AssertionError("the pbs_tok_held task is gone — this test is stale")


def held(result: dict | None) -> bool:
    rendered = jinja2.Environment().from_string(_condition()).render(  # noqa: S701
        vault_secret_result=result if result is not None else {},
        pbs_pve_backup_user=USER,
        pbs_pve_backup_token=TOKEN,
    )
    return rendered.strip() == "True"


def test_the_real_regression_a_stale_auth_id_is_not_held():
    """Exactly #570: a value is present, but for a user PBS no longer has."""
    assert not held({"tokenid": OLD, "value": "something"})


def test_a_matching_token_is_held():
    assert held({"tokenid": LIVE, "value": "something"})


def test_absent_is_not_held():
    assert not held({})
    assert not held(None)


def test_a_tokenid_with_no_value_is_not_held():
    assert not held({"tokenid": LIVE})
    assert not held({"tokenid": LIVE, "value": ""})


def test_a_value_with_no_tokenid_is_not_held():
    assert not held({"value": "something"})


def test_the_play_no_longer_reads_the_token_off_disk():
    body = PLAY.read_text()
    assert "pbs-pve-backup-token.json" not in body
    assert "lookup('file'" not in body
