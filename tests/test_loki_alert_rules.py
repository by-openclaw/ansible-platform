"""Alerts on logs (roles/loki): the rule file must stay a valid rule file after templating.

A rule the ruler cannot parse is silently left out — the role checks that at run time; this
checks the shape before anything is deployed.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")
jinja2 = pytest.importorskip("jinja2")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "roles" / "loki" / "templates" / "rules.yml.j2").read_text()
VARS = {
    "loki_rule_interval": "1m",
    "loki_vault_audit_selector": '{job="vault_audit"}',
    "loki_vault_people_area": "users",
    "loki_vault_automation_login": "ansible-deploy",
    "loki_vault_oidc_mount": "oidc",
    "loki_vault_window": "5m",
    "loki_vault_audit_silence": "26h",
}
RULES = yaml.safe_load(jinja2.Environment().from_string(TEMPLATE).render(**VARS))["groups"][0]["rules"]  # noqa: S701


def test_every_rule_is_complete():
    assert [r["alert"] for r in RULES] == [
        "VaultPersonAreaTouchedByAnother",
        "VaultPolicyChangedOutsideAutomation",
        "VaultRootTokenInUse",
        "VaultAuditLogSilent",
    ]
    for rule in RULES:
        assert rule["labels"]["severity"] in ("critical", "warning"), rule["alert"]
        assert rule["annotations"]["summary"], rule["alert"]
        assert VARS["loki_vault_audit_selector"] in rule["expr"], rule["alert"]
        assert rule["expr"].count("(") == rule["expr"].count(")"), rule["alert"]
        assert rule["expr"].count("{") == rule["expr"].count("}"), rule["alert"]


def test_automation_is_the_only_exception_and_a_person_owns_their_area():
    area, policy = RULES[0]["expr"], RULES[1]["expr"]
    for expr in (area, policy):
        assert 'role!="ansible-deploy"' in expr
        assert 'type="response"' in expr       # a refused attempt is a response with an error: it counts
    assert '(trimPrefix "oidc-" .who)' in area  # the caller's own name, compared with the path
    assert 'printf "/users/%s/"' in area
    assert 'owner="no"' in area


def test_what_the_alert_says_names_who_did_it():
    assert "$labels.who" in RULES[0]["annotations"]["summary"]
    assert "$labels.path" in RULES[1]["annotations"]["summary"]


def test_the_silence_window_is_longer_than_a_day():
    assert "absent_over_time" in RULES[3]["expr"] and "[26h]" in RULES[3]["expr"]
