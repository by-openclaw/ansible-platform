"""Vault's audit log (SEC-07) is written by the ACTIVE member — any of them.

The variable that makes promtail ship the file was set for the first member only: when another
member became active, no audit entry reached the log store (found 2026-10-11 after 38 hours).
It belongs to the group that holds every member.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parents[1]
INV = ROOT / "inventories" / "prod"
VAR = "promtail_vault_audit_log"


def _children(groups: dict, name: str) -> dict:
    for key, value in groups.items():
        if key == name:
            return value
        if isinstance(value, dict):
            found = _children(value.get("children") or {}, name)
            if found is not None:
                return found
    return None


def test_the_cluster_group_holds_the_first_member_and_the_replicas():
    hosts = yaml.safe_load((INV / "hosts.yml").read_text())
    cluster = _children(hosts, "vault_cluster")
    assert cluster is not None, "no vault_cluster group — this test is stale"
    assert set(cluster["children"]) >= {"vault", "vault_replicas"}


def test_the_audit_file_is_shipped_from_every_member():
    cluster_vars = yaml.safe_load((INV / "group_vars" / "vault_cluster.yml").read_text())
    assert cluster_vars.get(VAR), "the cluster group must name the audit file for promtail"


def test_no_narrower_group_sets_it():
    for narrower in ("vault.yml", "vault_replicas.yml"):
        path = INV / "group_vars" / narrower
        if path.exists():
            assert VAR not in (yaml.safe_load(path.read_text()) or {}), f"{narrower} would shadow the cluster-wide value"
