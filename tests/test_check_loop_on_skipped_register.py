"""The loop guard exists because a dry-run of the Discord play died on
"No last item, sequence was empty": a task looped over a register that --check
leaves empty, and `when: not ansible_check_mode` does not save it, because
Ansible evaluates a task's loop BEFORE its when.

These tests pin both halves: it catches that shape, and it stays quiet on the
shapes that are fine — otherwise it becomes a guard people learn to ignore.
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


guard = _load("check_loop_on_skipped_register")

SKIPPED = """---
- name: "Reconcile the thing"
  ansible.builtin.command:
    argv: [python3, reconcile.py]
  register: run_out
  changed_when: true

- name: "Act on what it produced"
  ansible.builtin.debug:
    msg: "{{ item }}"
  loop: "{{ (run_out.stdout_lines | last | from_json).items }}"
"""

READ_ONLY = """---
- name: "Read the current value"
  ansible.builtin.command:
    argv: [vault, kv, get, path]
  register: read_out
  check_mode: false
  changed_when: false

- name: "Act on it"
  ansible.builtin.debug:
    msg: "{{ item }}"
  loop: "{{ read_out.stdout_lines }}"
"""

WITH_DEFAULT = """---
- name: "Reconcile the thing"
  ansible.builtin.command:
    argv: [python3, reconcile.py]
  register: run_out

- name: "Act on what it produced"
  ansible.builtin.debug:
    msg: "{{ item }}"
  loop: "{{ run_out.stdout_lines | default([]) }}"
"""


def _scan(tmp_path, text):
    f = tmp_path / "main.yml"
    f.write_text(text)
    return guard.scan(f)


def test_a_loop_over_a_check_skipped_register_is_caught(tmp_path):
    hits = _scan(tmp_path, SKIPPED)
    assert len(hits) == 1
    _line, name, origin, _text = hits[0]
    assert name == "run_out"
    assert "command" in origin


def test_a_read_only_probe_is_not_flagged(tmp_path):
    # check_mode: false means the task DOES run under --check, so its register is filled
    assert _scan(tmp_path, READ_ONLY) == []


def test_a_safe_default_is_not_flagged(tmp_path):
    # the fix the guard asks for: the loop can no longer end the play
    assert _scan(tmp_path, WITH_DEFAULT) == []


def test_the_repository_is_clean():
    """The tree this test ships with must pass its own guard."""
    assert guard.main([]) == 0
