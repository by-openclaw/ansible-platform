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
        windows_template_image_index=2, platform_org="example", windows_template_admin_password="x" * 24,
        windows_template_removed_features=["FeatureA", "FeatureB"], windows_template_disabled_services=["Svc"],
        windows_template_power_scheme="scheme-guid",
        windows_template_input_locale="080c:00000813", windows_template_system_locale="fr-BE",
        windows_template_user_locale="fr-BE", windows_template_ui_language="en-US",
        windows_template_timezone="Romance Standard Time",
    )


def test_first_logon_orders_are_a_dense_sequence():
    # the Order counter must cover the data-driven commands (features, power) and stay
    # 1..N without gaps or duplicates — Windows runs FirstLogonCommands by Order
    root = ET.fromstring(_render())
    flc = [e for e in root.iter() if e.tag.endswith("FirstLogonCommands")][0]
    orders = [int(o.text) for o in flc.iter() if o.tag.endswith("Order")]
    assert orders == list(range(1, len(orders) + 1)), orders
    text = _render()
    assert "FeatureName:FeatureA" in text and "FeatureName:FeatureB" in text
    assert text.index("FeatureName:FeatureA") < text.index("/StartComponentCleanup") < text.index("sysprep.exe")


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


def _render_conf():
    # Ansible's templating runs with trim_blocks=True (and the platform's lstrip default):
    # render EXACTLY like that, or a passing test hides a glued-lines template (an inline
    # Jinja comment ate the newline after a value — two broken templates, 2026-10-14).
    conf_tpl = (ROOT / "roles" / "windows_template" / "templates" / "cloudbase-init.conf.j2").read_text()
    return jinja2.Environment(trim_blocks=True).from_string(conf_tpl).render()


def test_cloudbase_conf_every_line_is_whole():
    for line in _render_conf().splitlines():
        assert line == "" or line.startswith(("#", "[")) or line.count("=") >= 1, line
    # the glued-lines regression: each known option sits alone on its line
    lines = _render_conf().splitlines()
    assert "inject_user_password=true" in lines  # pragma: allowlist secret — a boolean option name
    assert "first_logon_behaviour=no" in lines


def test_cloudbase_conf_values_carry_no_inline_comments():
    # oslo.config keeps everything after '=' as the value: an inline "# comment" breaks
    # the boolean parse and cloudbase-init dies on start (exit 1067, no log) — seen live
    # on the first clones, 2026-10-14.
    import configparser
    import io

    text = _render_conf()
    parser = configparser.ConfigParser(comment_prefixes=("#",), inline_comment_prefixes=None)
    parser.read_string(text)
    for key, value in parser["DEFAULT"].items():
        assert "#" not in value, f"{key} carries an inline comment into its value: {value!r}"
    assert parser["DEFAULT"]["inject_user_password"] == "true"  # pragma: allowlist secret — a boolean option name


def test_cloudbase_conf_logdir_exists_in_the_image():
    # oslo_log opens logdir/logfile before anything else; a dir nothing creates kills
    # the service on start (exit 1067). The MSI ships its own log dir — use that one.
    text = _render_conf()
    logdir = [line for line in text.splitlines() if line.startswith("logdir=")][0]
    assert logdir == "logdir=C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\log\\"
