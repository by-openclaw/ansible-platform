"""The no-embedded-scripts guard decides whether a change lands, and its counts are the progress
number of the "provisioning is Ansible" refactor. It must count a script written inside a task
and stay quiet on what only looks like one — a guard that cries wolf gets switched off.

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


guard = _load("check_no_embedded_scripts")


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """An empty repository the guard reads instead of the real one."""
    (tmp_path / "roles").mkdir()
    (tmp_path / "playbooks").mkdir()
    monkeypatch.setattr(guard, "ROOT", tmp_path)
    monkeypatch.setattr(guard, "BASELINE", tmp_path / "baseline.json")

    def write(rel: str, text: str) -> None:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    return write


def test_a_shell_task_is_counted_with_or_without_the_collection_prefix(tree):
    tree("roles/a/tasks/main.yml", "- name: x\n  ansible.builtin.shell: echo a | wc -l\n- name: y\n  shell: echo b\n")
    assert guard.scan()["shell_tasks"] == {"roles/a/tasks/main.yml": 2}


def test_the_login_shell_of_the_user_module_is_not_a_shell_task(tree):
    tree("roles/a/tasks/main.yml", "- name: account\n  ansible.builtin.user:\n    name: svc\n    shell: /usr/sbin/nologin\n")
    assert guard.scan()["shell_tasks"] == {}


def test_a_shell_task_inside_block_rescue_and_always_is_counted(tree):
    tree(
        "playbooks/p.yml",
        "- hosts: all\n  tasks:\n    - name: b\n      block:\n        - name: one\n          ansible.builtin.shell: a\n"
        "      rescue:\n        - name: two\n          ansible.builtin.shell: b\n"
        "      always:\n        - name: three\n          ansible.builtin.shell: c\n",
    )
    assert guard.scan()["shell_tasks"] == {"playbooks/p.yml": 3}


def test_a_plain_command_with_arguments_is_not_counted(tree):
    tree("roles/a/tasks/main.yml", "- name: x\n  ansible.builtin.command:\n    argv: [docker, ps]\n")
    found = guard.scan()
    assert all(found[category] == {} for category in guard.CATEGORIES)


def test_an_interpreter_given_a_program_on_its_command_line_is_counted_per_line(tree):
    tree(
        "roles/a/tasks/main.yml",
        "- name: x\n  ansible.builtin.command:\n    argv: [docker, exec, c, python3, -c, 'print(1)']\n"
        "- name: unit\n  ansible.builtin.set_fact:\n    cmd: \"/bin/sh -c 'a | b'\"\n    other: \"/bin/bash -c 'c'\"\n",
    )
    assert guard.scan()["inline_interpreters"] == {"roles/a/tasks/main.yml": 3}


def test_a_unit_template_is_read_as_text_and_a_comment_is_not_counted(tree):
    tree("roles/a/templates/unit.service.j2", "ExecStart=/bin/sh -c 'x | y'\n# /bin/sh -c in a comment\n")
    assert guard.scan()["inline_interpreters"] == {"roles/a/templates/unit.service.j2": 1}


def test_an_argument_list_that_hands_a_program_to_an_interpreter_is_counted(tree):
    tree(
        "roles/a/tasks/main.yml",
        "- name: flow list\n  ansible.builtin.command:\n    argv: [docker, exec, c, /usr/bin/python3, -c, 'print(1)']\n"
        "- name: block list\n  community.docker.docker_container_exec:\n    container: c\n    argv:\n      - php\n      - -r\n      - 'echo 1;'\n"
        "- name: an interpreter running a module is not a program on the command line\n"
        "  ansible.builtin.command:\n    argv: [python3, -m, venv, /opt/x]\n",
    )
    assert guard.scan()["inline_interpreters"] == {"roles/a/tasks/main.yml": 2}


def test_a_program_in_a_role_is_counted_and_an_application_config_is_not(tree, monkeypatch):
    monkeypatch.setattr(guard, "APP_CONFIG", {"roles/gitlab/templates/gitlab.rb.j2": "GitLab's own configuration"})
    tree("roles/a/files/reconcile.py", "print(1)\n")
    tree("roles/a/templates/job.sh.j2", "#!/bin/sh\n")
    tree("roles/gitlab/templates/gitlab.rb.j2", "external_url 'x'\n")
    tree("roles/a/files/data.json", "{}\n")
    assert guard.scan()["script_files"] == {"roles/a/files/reconcile.py": 1, "roles/a/templates/job.sh.j2": 1}


def test_a_program_handed_to_an_application_console_is_counted_however_the_command_is_written(tree):
    tree(
        "roles/a/tasks/main.yml",
        "- name: one line\n  ansible.builtin.command:\n    argv: [docker, exec, gitlab, gitlab-rails, runner, 'puts 1']\n"
        "- name: a templated list\n  ansible.builtin.command:\n"
        "    argv: \"{{ gitlab_exec + [gitlab_container, 'gitlab-rails', 'runner', code] }}\"\n"
        "- name: one word per line\n  ansible.builtin.command:\n    argv:\n      - docker\n      - exec\n      - server\n"
        "      - ak\n      - shell\n      - -c\n      - |\n        print(1)\n"
        "- name: a command line\n  ansible.builtin.command:\n    cmd: docker exec -i backend python manage.py shell\n"
        "- name: NetBox's variant\n  ansible.builtin.command:\n    cmd: docker exec -i netbox /opt/netbox/netbox/manage.py nbshell\n",
    )
    assert guard.scan()["console_programs"] == {"roles/a/tasks/main.yml": 5}


def test_a_task_name_or_a_comment_that_mentions_a_console_is_not_counted(tree):
    tree(
        "roles/a/tasks/main.yml",
        "# formerly: gitlab-rails runner reconcile.rb\n"
        "- name: \"The directory callers stage for gitlab-rails runner\"\n  ansible.builtin.file:\n    path: /srv/x\n    state: directory\n",
    )
    assert guard.scan()["console_programs"] == {}


def test_an_application_command_that_takes_no_program_is_not_a_console_program(tree):
    tree(
        "roles/a/tasks/main.yml",
        "- name: a management command\n  ansible.builtin.command:\n    argv: [docker, exec, netbox, /opt/netbox/netbox/manage.py, housekeeping]\n"
        "- name: a path that holds the word\n  ansible.builtin.command:\n    argv: [cat, /opt/gitlab/embedded/service/gitlab-rails/VERSION]\n"
        "- name: another tool\n  ansible.builtin.command:\n    argv: [gitlab-ctl, reconfigure]\n"
        "- name: weed shell reads commands, not a program\n  ansible.builtin.command:\n    argv: [weed, shell, -master, m]\n",
    )
    assert guard.scan()["console_programs"] == {}


def test_a_shell_command_in_a_pipe_lookup_is_counted(tree):
    tree(
        "playbooks/p.yml",
        "- hosts: all\n  tasks:\n    - name: t\n      ansible.builtin.set_fact:\n        started: \"{{ lookup('pipe', 'date +%s') }}\"\n"
        "        other: \"{{ lookup('file', 'x') }}{{ query(\\\"pipe\\\", 'id') }}\"\n",
    )
    assert guard.scan()["pipe_lookups"] == {"playbooks/p.yml": 2}


def test_a_program_written_by_a_task_is_a_script_file_and_a_written_config_is_not(tree):
    tree(
        "roles/a/tasks/main.yml",
        "- name: a staged program\n  ansible.builtin.copy:\n    dest: /tmp/reconcile.py\n    content: |\n      print(1)\n"
        "- name: a configuration file\n  ansible.builtin.copy:\n    dest: /etc/app/app.conf\n    content: |\n      key = value\n"
        "- name: a file shipped from the role\n  ansible.builtin.copy:\n    src: seed.rb\n    dest: /srv/scripts/seed.rb\n",
    )
    assert guard.scan()["script_files"] == {"roles/a/tasks/main.yml": 1}


def test_archived_playbooks_are_not_read(tree):
    tree("playbooks/archive/old.yml", "- hosts: all\n  tasks:\n    - name: x\n      ansible.builtin.shell: a\n")
    assert guard.scan()["shell_tasks"] == {}


def test_archived_task_files_of_a_role_are_not_read(tree):
    tree("roles/fw/tasks/_archive/old.yml", "- name: x\n  ansible.builtin.raw: a\n- name: y\n  ansible.builtin.shell: b\n")
    found = guard.scan()
    assert found["raw_module"] == {} and found["shell_tasks"] == {}


def test_a_file_that_only_has_archive_in_its_name_is_still_read(tree):
    tree("roles/svc/tasks/archive_data.yml", "- name: x\n  ansible.builtin.shell: a\n")
    assert guard.scan()["shell_tasks"] == {"roles/svc/tasks/archive_data.yml": 1}


def test_a_vault_tagged_value_does_not_stop_the_reading(tree):
    tree("roles/a/tasks/main.yml", "- name: x\n  ansible.builtin.debug:\n    msg: !vault |\n      abc\n- name: y\n  ansible.builtin.shell: a\n")
    assert guard.scan()["shell_tasks"] == {"roles/a/tasks/main.yml": 1}


def test_the_ratchet_refuses_a_count_above_the_baseline_and_names_the_file(tree):
    tree("roles/a/tasks/main.yml", "- name: x\n  ansible.builtin.shell: a\n- name: y\n  ansible.builtin.shell: b\n")
    rose, fell = guard.ratchet(guard.scan(), {"shell_tasks": {"roles/a/tasks/main.yml": 1}})
    assert rose == ["shell_tasks: roles/a/tasks/main.yml has 2, the baseline allows 1"]
    assert fell is False


def test_the_ratchet_refuses_a_script_in_a_file_the_baseline_does_not_know(tree):
    tree("roles/new/tasks/main.yml", "- name: x\n  ansible.builtin.shell: a\n")
    rose, _ = guard.ratchet(guard.scan(), {"shell_tasks": {}})
    assert rose == ["shell_tasks: roles/new/tasks/main.yml has 1, the baseline allows 0"]


def test_the_ratchet_lowers_the_baseline_when_a_script_is_gone_and_fails_once(tree, tmp_path):
    tree("roles/a/tasks/main.yml", "- name: x\n  ansible.builtin.command:\n    argv: [true]\n")
    (tmp_path / "baseline.json").write_text('{"shell_tasks": {"roles/a/tasks/main.yml": 1}}', encoding="utf-8")
    assert guard.main(["--ratchet"]) == 1
    assert '"shell_tasks": {}' in (tmp_path / "baseline.json").read_text(encoding="utf-8")
    assert guard.main(["--ratchet"]) == 0


def test_moving_a_script_to_another_file_does_not_pass_as_a_removal(tree):
    tree("roles/b/tasks/main.yml", "- name: x\n  ansible.builtin.shell: a\n")
    rose, fell = guard.ratchet(guard.scan(), {"shell_tasks": {"roles/a/tasks/main.yml": 1}})
    assert rose and fell
