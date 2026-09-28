"""The image-pin guard runs on every commit and in CI. A moving tag lets a redeploy change the
running software without a diff in this repo, so the guard must catch each one in code and stay
quiet on prose that names them — otherwise it becomes a guard people learn to ignore.

It replaced scripts/check_image_pins.sh. The grep-recursive tests pin how that script read the
trees, so the port cannot drift from it unnoticed.

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


guard = _load("check_image_pins")


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A scratch tree as the repo root: write {path: text or bytes}, get what the guard reports.
    It is no git repo, so main() scans it where it stands, as the .sh did outside a repo."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    def write(files: dict[str, str | bytes]) -> list[str]:
        for rel, content in files.items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return guard.moving_tags()

    return write


class TestAMovingTagInCodeFails:
    @pytest.mark.parametrize("tag", ["latest", "stable", "edge", "main", "master"])
    def test_each_moving_tag_is_caught(self, tree, tag):
        assert tree({"roles/web/tasks/main.yml": f'image: "nginx:{tag}"\n'}) == [
            f'roles/web/tasks/main.yml:1:image: "nginx:{tag}"'
        ]

    @pytest.mark.parametrize("root", ["roles", "playbooks", "inventories"])
    def test_all_three_trees_are_scanned(self, tree, root):
        assert tree({f"{root}/x/any.yml": "image: nginx:latest\n"}) == [
            f"{root}/x/any.yml:1:image: nginx:latest"
        ]

    def test_a_tag_followed_by_a_space_is_caught(self, tree):
        assert tree({"roles/web/tasks/main.yml": "cmd: docker pull busybox:master --quiet\n"}) == [
            "roles/web/tasks/main.yml:1:cmd: docker pull busybox:master --quiet"
        ]


class TestAPinIsNotAMovingTag:
    @pytest.mark.parametrize(
        "image", ["nginx:1.27.3", "jitsi/web:stable-9955", "app:latest-2026", "nginx@sha256:0123abcd"]
    )
    def test_an_immutable_tag_passes(self, tree, image):
        assert tree({"roles/web/tasks/main.yml": f'image: "{image}"\n'}) == []


class TestProseIsNotCode:
    @pytest.mark.parametrize(
        "line",
        [
            "# never :latest",
            "    # pinned, never :latest",
            'image: "nginx:1.27.3"   # was :latest',
        ],
    )
    def test_a_comment_is_ignored(self, tree, line):
        assert tree({"roles/web/defaults/main.yml": line + "\n"}) == []

    def test_markdown_is_ignored(self, tree):
        assert tree({"roles/web/README.md": "image: nginx:latest\n"}) == []

    def test_an_archived_file_is_ignored(self, tree):
        assert tree({"playbooks/archive/old.yml": 'image: "nginx:latest"\n'}) == []


class TestTheTreesAreReadLikeGrepRecursive:
    def test_a_dotfile_is_scanned(self, tree):
        assert tree({"roles/web/.hidden.yml": "image: nginx:latest\n"}) == [
            "roles/web/.hidden.yml:1:image: nginx:latest"
        ]

    def test_a_last_line_without_a_newline_is_scanned(self, tree):
        assert tree({"roles/web/x.yml": "image: nginx:latest"}) == ["roles/web/x.yml:1:image: nginx:latest"]

    def test_a_binary_file_is_skipped(self, tree):
        assert tree({"roles/web/files/blob": b'image: "nginx:latest"\n\0'}) == []

    def test_a_symlink_inside_a_tree_is_not_followed(self, tree, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "x.yml").write_text('image: "nginx:latest"\n')
        (tmp_path / "roles").mkdir()
        (tmp_path / "roles" / "file.yml").symlink_to(outside / "x.yml")
        (tmp_path / "roles" / "dir").symlink_to(outside)
        assert tree({}) == []


class TestTheOutputMatchesTheShellVersion:
    def test_a_failure_lists_each_record_and_exits_1(self, tree, capsys):
        tree({"roles/web/tasks/main.yml": 'image: "nginx:latest"\n'})
        assert guard.main() == 1
        assert capsys.readouterr().out == '  moving tag: roles/web/tasks/main.yml:1:image: "nginx:latest"\n'

    def test_a_clean_tree_prints_the_ok_line_and_exits_0(self, tree, capsys):
        tree({"roles/web/tasks/main.yml": 'image: "nginx:1.27.3"\n'})
        assert guard.main() == 0
        assert capsys.readouterr().out == guard.OK + "\n"


class TestTheGuardRunsOverTheRealTree:
    def test_the_repository_is_clean(self, monkeypatch):
        """The tree this test ships with must pass its own guard."""
        monkeypatch.chdir(ROOT)
        assert guard.main() == 0
