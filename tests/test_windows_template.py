"""The Windows answer file must stay a valid answer file after templating."""

from __future__ import annotations

import pathlib
import xml.etree.ElementTree as ET

import pytest

jinja2 = pytest.importorskip("jinja2")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = (ROOT / "roles" / "windows_template" / "templates" / "autounattend.xml.j2").read_text()


def _render():
    env = jinja2.Environment()  # noqa: S701 — an answer file, not HTML
    return env.from_string(TPL).render(
        windows_template_image_index=2, platform_org="example", windows_template_admin_password="x" * 24
    )


def test_it_parses_and_installs_the_gui_standard_image():
    root = ET.fromstring(_render())
    text = _render()
    assert "<Key>/IMAGE/INDEX</Key>" in text and "<Value>2</Value>" in text
    assert root.tag.endswith("unattend")


def test_no_product_key_on_evaluation_media():
    assert "ProductKey" not in _render()


def test_the_build_ends_generalised_and_off():
    text = _render()
    assert "/generalize" in text and "/shutdown" in text
    assert text.index("qemu-ga.msi") < text.index("CloudbaseInitSetup.msi") < text.index("sysprep.exe")


def test_cloudbase_conf_values_carry_no_inline_comments():
    # oslo.config keeps everything after '=' as the value: an inline "# comment" breaks
    # the boolean parse and cloudbase-init dies on start (exit 1067, no log) — seen live
    # on the first clones, 2026-10-14.
    import configparser
    import io

    conf_tpl = (ROOT / "roles" / "windows_template" / "templates" / "cloudbase-init.conf.j2").read_text()
    text = jinja2.Environment().from_string(conf_tpl).render()
    parser = configparser.ConfigParser(comment_prefixes=("#",), inline_comment_prefixes=None)
    parser.read_string(text)
    for key, value in parser["DEFAULT"].items():
        assert "#" not in value, f"{key} carries an inline comment into its value: {value!r}"
    assert parser["DEFAULT"]["inject_user_password"] == "true"  # pragma: allowlist secret — a boolean option name


def test_cloudbase_conf_logdir_exists_in_the_image():
    # oslo_log opens logdir/logfile before anything else; a dir nothing creates kills
    # the service on start (exit 1067). The MSI ships its own log dir — use that one.
    conf_tpl = (ROOT / "roles" / "windows_template" / "templates" / "cloudbase-init.conf.j2").read_text()
    text = jinja2.Environment().from_string(conf_tpl).render()
    logdir = [line for line in text.splitlines() if line.startswith("logdir=")][0]
    assert logdir == "logdir=C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\log\\"
