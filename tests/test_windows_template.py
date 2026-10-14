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
