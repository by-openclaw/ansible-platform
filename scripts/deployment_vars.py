"""Render {{ platform_* }} deployment tokens in raw catalog files.

The FW scripts read inventories/<env>/group_vars/opnsense.yml directly (no
Ansible in the loop), so the Jinja deployment variables (platform_domain,
platform_org, platform_env — the naming/0001 §9 single-source manifest) must
be substituted here, from the same inventory's group_vars/all/deployment.yml,
before yaml parsing. Ansible itself renders the same tokens natively.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_TOKEN = re.compile(r"\{\{\s*(platform_[a-z_]+)\s*\}\}")


def render_deployment_tokens(catalog_path: Path) -> str:
    """Return the catalog text with all {{ platform_* }} tokens resolved."""
    text = catalog_path.read_text()
    manifest = catalog_path.parent / "all" / "deployment.yml"
    try:
        raw = yaml.safe_load(manifest.read_text()) or {}
    except FileNotFoundError:
        raw = {}
    tokens = {k: str(v) for k, v in raw.items() if isinstance(k, str)}

    def _sub(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in tokens:
            raise SystemExit(
                f"Unresolved deployment token '{{{{ {name} }}}}' in {catalog_path} "
                f"— define it in {manifest}"
            )
        return tokens[name]

    return _TOKEN.sub(_sub, text)
