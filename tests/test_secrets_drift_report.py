"""The drift report exists because `secrets-to-vault.yml` can only say "differs",
and the obvious way to find out more — diffing a file against Vault — prints
credentials to a terminal.

So the one property that matters is that the report emits key NAMES and never a
value. These render the real expression out of playbooks/tasks/secrets_drift_one.yml
and assert that a planted secret never appears in what comes out.
"""

from __future__ import annotations

import json
import pathlib

import pytest

yaml = pytest.importorskip("yaml")
jinja2 = pytest.importorskip("jinja2")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASK = ROOT / "playbooks" / "tasks" / "secrets_drift_one.yml"

# Distinctive enough that a substring check is meaningful.
PLANTED = "hunter2-PLANTED-SECRET-VALUE"  # pragma: allowlist secret


def _diff_expression() -> str:
    for task in yaml.safe_load(TASK.read_text()):
        fact = task.get("ansible.builtin.set_fact", {})
        if "_dr_finding" in fact:
            return fact["_dr_finding"]
    raise AssertionError("the _dr_finding task is gone — this test is stale")


def diff(file_doc: dict, vault_doc: dict) -> dict:
    env = jinja2.Environment()  # noqa: S701 — building a report, not HTML
    env.filters["intersect"] = lambda a, b: [x for x in a if x in b]
    env.filters["difference"] = lambda a, b: [x for x in a if x not in b]
    env.filters["to_json"] = json.dumps
    rendered = env.from_string(_diff_expression()).render(
        _dr_path="prod/svc/key", _dr_file=file_doc, _dr_vault=vault_doc
    )
    return json.loads(rendered)


def test_a_stale_password_is_named():
    out = diff({"password": PLANTED}, {"password": "the-live-one"})  # pragma: allowlist secret
    assert out["value_differs"] == ["password"]


def test_a_value_never_appears_in_the_output():
    """The whole point. Plant a secret on each side and in a shared key."""
    out = diff(
        {"password": PLANTED, "url": "https://x", "only_here": PLANTED},
        {"password": "other", "url": "https://x", "rotated": PLANTED},  # pragma: allowlist secret
    )
    blob = json.dumps(out)
    assert PLANTED not in blob, f"the report leaked a value: {blob}"
    assert "other" not in blob
    assert "https://x" not in blob


def test_extra_bookkeeping_is_distinguished_from_a_differing_secret():
    """netbox was exactly this: identical password, Vault carrying a 'rotated' key.
    Reporting that as 'differs' is what made 12 findings unreadable."""
    out = diff({"password": "same"}, {"password": "same", "rotated": "2026-09-01"})
    assert out["value_differs"] == []
    assert out["only_in_vault"] == ["rotated"]
    assert out["only_in_file"] == []


def test_keys_missing_from_vault_are_named():
    out = diff({"password": "p", "url": "u"}, {"password": "p"})
    assert out["only_in_file"] == ["url"]
    assert out["value_differs"] == []


def test_identical_documents_produce_nothing():
    out = diff({"password": "p", "url": "u"}, {"password": "p", "url": "u"})
    assert out["only_in_file"] == []
    assert out["only_in_vault"] == []
    assert out["value_differs"] == []


def test_several_differing_keys_are_all_named_and_sorted():
    out = diff(
        {"password": "a", "token": "a", "url": "same"},
        {"password": "b", "token": "b", "url": "same"},
    )
    assert out["value_differs"] == ["password", "token"]


def test_every_task_that_can_see_a_value_is_no_log():
    tasks = yaml.safe_load(TASK.read_text())
    offenders = [
        t.get("name")
        for t in tasks
        if any(k in str(t) for k in ("_dr_file", "_dr_vault", "vault_root_token", "_dr_cur"))
        and "ansible.builtin.include_tasks" not in t
        and not t.get("no_log")
    ]
    # The append task handles only the already-sanitised finding.
    offenders = [o for o in offenders if o and "Keep it only if" not in o]
    assert not offenders, f"these could print a secret: {offenders}"
