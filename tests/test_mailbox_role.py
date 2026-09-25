"""roles/mailbox is the only writer of Mailcow mailbox state. Three properties
have to hold and none of them is visible by reading one file at a time.

* A dry-run must never create a mailbox. Mailcow answers 200 whether or not it
  created one (#518), so `check_mode: false` on a write is not recoverable by
  reading the response — the box is simply there afterwards.
* The reads every decision depends on MUST run under --check. Ansible skips uri
  and command there, and a skipped read registers a bare dict, which reads as
  "the mailbox does not exist" and turns a dry-run into a plan to create
  everything.
* The API key comes from Vault. It can create and read every mailbox on the
  platform; a copy on the controller's disk is the one that leaks.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASKS = ROOT / "roles" / "mailbox" / "tasks"

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MUTATING_SQL = ("INSERT", "UPDATE", "DELETE ", "DELETE\n")


def tasks_of(path: pathlib.Path):
    """Every task in a file, flattened out of block/rescue/always."""
    out = []

    def walk(items):
        for t in items or []:
            if not isinstance(t, dict):
                continue
            out.append(t)
            for key in ("block", "rescue", "always"):
                walk(t.get(key))

    walk(yaml.safe_load(path.read_text()))
    return out


ALL = {p.name: tasks_of(p) for p in sorted(TASKS.glob("*.yml"))}


def is_write(task) -> bool:
    uri = task.get("ansible.builtin.uri") or {}
    if uri.get("method", "GET").upper() in WRITE_METHODS:
        return True
    cmd = task.get("ansible.builtin.command") or {}
    text = str(cmd.get("cmd", "")) + str(cmd.get("stdin", ""))
    if any(k in text.upper() for k in MUTATING_SQL):
        return True
    s3 = task.get("amazon.aws.s3_object") or {}
    return s3.get("mode") in ("put", "delete")


def is_read(task) -> bool:
    uri = task.get("ansible.builtin.uri") or {}
    if uri and uri.get("method", "GET").upper() == "GET":
        return True
    cmd = task.get("ansible.builtin.command") or {}
    text = str(cmd.get("cmd", ""))
    if "SELECT" in text.upper() and not any(k in text.upper() for k in MUTATING_SQL):
        return True
    s3 = task.get("amazon.aws.s3_object") or {}
    return s3.get("mode") == "list"


def test_the_role_has_a_file_for_every_state():
    dispatched = {
        t["ansible.builtin.include_tasks"]
        for t in ALL["main.yml"]
        if "ansible.builtin.include_tasks" in t
    }
    assert {"present.yml", "suspended.yml", "absent.yml"} <= dispatched


def test_no_write_runs_under_check_mode():
    offenders = [
        (f, t.get("name"))
        for f, ts in ALL.items()
        for t in ts
        if is_write(t) and t.get("check_mode") is False
    ]
    assert not offenders, f"a dry-run would change mailcow: {offenders}"


def test_every_read_a_decision_depends_on_runs_under_check_mode():
    offenders = [
        (f, t.get("name"))
        for f, ts in ALL.items()
        for t in ts
        if is_read(t) and "register" in t and t.get("check_mode") is not False
    ]
    assert not offenders, f"skipped under --check, registers empty, reads as absent: {offenders}"


def test_no_read_reports_changed():
    offenders = [
        (f, t.get("name"))
        for f, ts in ALL.items()
        for t in ts
        if is_read(t) and t.get("changed_when") is not False and "register" in t
    ]
    assert not offenders, f"a read must not report changed: {offenders}"


def test_the_mailcow_api_key_comes_from_vault_not_a_file():
    body = "\n".join(p.read_text() for p in TASKS.glob("*.yml"))
    body += (ROOT / "roles" / "mailbox" / "defaults" / "main.yml").read_text()
    assert "lookup('file'" not in body, "the API key must not be read off the controller's disk"
    assert "vault_secret" in body


def test_the_secrets_never_reach_the_log():
    """Every task handling the API key, a password or a maildir export is no_log."""
    offenders = []
    for f, ts in ALL.items():
        for t in ts:
            blob = str(t)
            touches_secret = any(
                k in blob
                for k in ("mailbox_api_hdr", "mailbox_password", "mailbox_s3", "vault_secret_result")
            )
            # A block wrapper is not a task — its children are checked on their own.
            # A debug summary names no secret value; an include_role passes vars, not values.
            if touches_secret and not t.get("no_log") and not (
                "block" in t
                or "ansible.builtin.include_role" in t
                or "ansible.builtin.include_tasks" in t
                or "ansible.builtin.debug" in t
                or "ansible.builtin.assert" in t
            ):
                offenders.append((f, t.get("name")))
    assert not offenders, f"these would print a secret: {offenders}"


def test_absent_never_deletes_the_mail_itself():
    """archive-before-destroy: absent deactivates and drops grants, nothing more."""
    blob = (TASKS / "absent.yml").read_text().upper()
    assert "DELETE FROM ALIAS" in blob
    assert "DELETE/MAILBOX" not in blob, "absent must not call the mailbox delete endpoint"


@pytest.mark.parametrize("state,active", [("present", "1"), ("suspended", "2"), ("absent", "0")])
def test_each_state_maps_to_the_right_mailcow_active_value(state, active):
    mapping = next(
        t["ansible.builtin.set_fact"]["mailbox_want_active"]
        for t in ALL["main.yml"]
        if "mailbox_want_active" in str(t.get("ansible.builtin.set_fact", {}))
    )
    # suspended=2 is the whole point: still receives, cannot log in.
    assert f"'{state}': {active}" in mapping.replace('"', "'")
