"""People reading in Vault (security/0001): the rights a group gets are read-only and exact.

The policy is rendered from the role's template with the inventory's data; the checks are on
what Vault would be given, not on the template's text.
"""

from __future__ import annotations

import pathlib
import re

import pytest

yaml = pytest.importorskip("yaml")
jinja2 = pytest.importorskip("jinja2")

ROOT = pathlib.Path(__file__).resolve().parents[1]
IDENTITY = yaml.safe_load((ROOT / "inventories" / "prod" / "group_vars" / "all" / "identity.yml").read_text())
LOGINS = IDENTITY["platform_service_logins"]
GROUPS = IDENTITY["platform_service_groups"]
TEMPLATE = (ROOT / "roles" / "vault" / "templates" / "people-policy.hcl.j2").read_text()
TASKS = ROOT / "roles" / "vault" / "tasks"


def _policy(group: str, paths: list[str]) -> list[tuple[str, list[str]]]:
    env = jinja2.Environment(trim_blocks=True)  # noqa: S701 — a policy text, not HTML
    env.filters["dirname"] = lambda p: p.rsplit("/", 1)[0] if "/" in p else ""
    text = env.from_string(TEMPLATE).render(
        vault_people_item={"group": group, "paths": paths}, vault_kv_path="secret", platform_env="prod"
    )
    rules = re.findall(r'path "([^"]+)" \{\s*capabilities = \[([^\]]*)\]', text)
    return [(p, [c.strip().strip('"') for c in caps.split(",")]) for p, caps in rules]


def test_every_login_belongs_to_a_service_with_an_administrators_group():
    for service in LOGINS:
        assert GROUPS.get(service, {}).get("admin"), f"{service}: no admin group to read its login"


def test_a_login_is_one_document_of_a_service_never_an_emergency_one():
    for service, paths in LOGINS.items():
        assert paths, service
        for path in paths:
            assert re.fullmatch(r"[a-z0-9-]+/[a-z0-9-]+", path), path
            assert not path.startswith(("break-glass/", "users/", "archive/")), path
            assert not path.endswith("/root"), path


@pytest.mark.parametrize("service", sorted(LOGINS))
def test_the_policy_reads_its_documents_and_lists_names_nothing_more(service):
    paths = LOGINS[service]
    rules = _policy(GROUPS[service]["admin"], paths)
    assert rules, "the template rendered no rule"
    for path, caps in rules:
        assert "*" not in path and "+" not in path, f"a wildcard would open more than declared: {path}"
        if path.startswith("secret/data/"):
            assert caps == ["read"], (path, caps)
            assert path.removeprefix("secret/data/prod/") in paths, path
        else:
            assert path.startswith("secret/metadata"), path
            assert caps in (["read"], ["list"]), (path, caps)
    assert sorted(p for p, _ in rules if p.startswith("secret/data/")) == sorted(f"secret/data/prod/{p}" for p in paths)


def test_no_rule_lets_a_person_write():
    for service, paths in LOGINS.items():
        for _, caps in _policy(GROUPS[service]["admin"], paths):
            assert not set(caps) & {"create", "update", "delete", "patch", "sudo"}


def test_every_include_carries_the_tag_to_what_it_includes():
    """`--tags people` must run the whole concern: an include's own tag stops at the include."""
    for task in yaml.safe_load((TASKS / "people.yml").read_text()):
        for module in ("ansible.builtin.include_tasks", "ansible.builtin.include_role"):
            if module in task:
                assert "people" in task[module]["apply"]["tags"], task["name"]


def test_the_proof_reads_no_document_and_removes_its_login():
    block = yaml.safe_load((TASKS / "people_verify.yml").read_text())[0]
    urls = [t["ansible.builtin.uri"]["url"] for t in block["block"] if "ansible.builtin.uri" in t]
    assert not any("/data/" in u for u in urls), "the proof must ask for capabilities, not read a document"
    assert any(u.endswith("/sys/capabilities-self") for u in urls)
    assert block["always"][0]["ansible.builtin.uri"]["method"] == "DELETE"


# --- the per-person area ------------------------------------------------------------------------
ACCESSOR = "auth_oidc_0000"
SELF = "{{identity.entity.aliases." + ACCESSOR + ".name}}"


ACCESS = [{"group": GROUPS[svc]["admin"], "paths": paths} for svc, paths in LOGINS.items()]


def _render(name: str) -> list[tuple[str, list[str]]]:
    env = jinja2.Environment(trim_blocks=True)  # noqa: S701 — a policy text, not HTML
    env.filters["flatten"] = lambda lists: [x for sub in lists for x in sub]   # Ansible's, one level
    text = env.from_string((ROOT / "roles" / "vault" / "templates" / name).read_text()).render(
        vault_kv_path="secret", platform_env="prod", vault_people_area="users", vault_people_accessor=ACCESSOR,
        vault_people_access=ACCESS,
    )
    rules = re.findall(r'path "([^"]+)" \{\s*capabilities = \[([^\]]*)\]', text)
    return [(p, [c.strip().strip('"') for c in caps.split(",")]) for p, caps in rules]


def test_a_person_reads_their_own_area_named_by_their_sign_in():
    rules = dict(_render("person-policy.hcl.j2"))
    assert rules[f"secret/data/prod/users/{SELF}/*"] == ["read"]
    assert rules[f"secret/metadata/prod/users/{SELF}/*"] == ["read", "list"]
    for path, caps in rules.items():
        assert not set(caps) & {"create", "update", "delete", "patch", "sudo"}, path
        if "/data/" in path:
            assert SELF in path, f"a value outside the person's own area: {path}"
        elif SELF not in path:
            assert caps == ["list"], f"outside the own area only names may be listed: {path}"


def test_an_administrator_is_refused_the_other_peoples_areas():
    rules = dict(_render("admins-policy.hcl.j2"))
    assert rules["secret/+/prod/users/*"] == ["deny"]
    # the person's own path has no wildcard before its end: Vault prefers it to the refusal
    own = f"secret/data/prod/users/{SELF}/*"
    assert own.index("*") > "secret/+/prod/users/*".index("+")


def test_the_person_proof_cleans_up_and_gives_its_token_back():
    block = yaml.safe_load((TASKS / "people_verify_person.yml").read_text())[0]
    urls = [t["ansible.builtin.uri"]["url"] for t in block["block"] if "ansible.builtin.uri" in t]
    assert any(u.endswith("/auth/token/revoke-self") for u in urls)
    assert any(u.endswith("/sys/capabilities-self") for u in urls)
    removed = [t["ansible.builtin.uri"] for t in block["always"]]
    assert all(u["method"] == "DELETE" for u in removed) and len(removed) == 2
    probe_paths = [block["vars"]["vault_people_probe_own"], block["vars"]["vault_people_probe_else"]]
    assert all("/data/" in p for p in probe_paths)   # asked about, never read
    assert not any("/data/" in u for u in urls)


def test_every_kind_of_person_is_proved():
    defaults = yaml.safe_load((ROOT / "roles" / "vault" / "defaults" / "main.yml").read_text())
    probes = defaults["vault_people_probes"]
    assert len({p["name"] for p in probes}) == 3, "one entity per kind of person (one name per sign-in method)"
    assert [len(p["policies"]) for p in probes] == [1, 2, 3]
    # a plain person and an administrator of Vault are refused every service login …
    assert all("vault_people_login_paths" in p["deny"] and p["read"] == [] for p in probes[:2])
    # … an administrator of Vault who is in a service's group reads that one only
    assert "vault_people_first_paths" in probes[2]["read"] and "difference" in probes[2]["deny"]


def test_an_administrator_of_vault_is_refused_every_service_login():
    rules = dict(_render("admins-policy.hcl.j2"))
    for paths in LOGINS.values():
        for path in paths:
            assert rules[f"secret/+/prod/{path}"] == ["deny"], path


@pytest.mark.parametrize("service", sorted(LOGINS))
def test_the_groups_own_exact_path_wins_over_that_refusal(service):
    """Vault prefers the path whose first wildcard comes later: the group's path has none."""
    for path, caps in _policy(GROUPS[service]["admin"], LOGINS[service]):
        if path.startswith("secret/data/"):
            assert "+" not in path and "*" not in path and caps == ["read"]
