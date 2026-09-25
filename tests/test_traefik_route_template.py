"""roles/traefik_route renders the file that decides who reaches which backend,
for every web service on the platform. Two things must hold and neither is
visible by reading the template.

1. A single-endpoint route renders exactly as it did before the multi-endpoint
   form existed. Thirty-one live routes go through this template; a stray blank
   line is harmless, a dropped ipAllowList is an exposure.
2. The network gate reaches EVERY endpoint of a multi-endpoint route. The whole
   risk of the second form is that it becomes a quiet way to lose the gate.

These render the real template with Ansible's Jinja settings, so they fail on a
change to the template itself, not to a copy of it.
"""

from __future__ import annotations

import pathlib
import re

import pytest

yaml = pytest.importorskip("yaml")
jinja2 = pytest.importorskip("jinja2")

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "roles" / "traefik_route" / "templates"


def _env() -> "jinja2.Environment":
    env = jinja2.Environment(  # noqa: S701 — config file, not HTML
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        trim_blocks=True,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    # The two Ansible filters the template uses.
    env.filters["bool"] = lambda v: (
        v if isinstance(v, bool) else str(v).strip().lower() in ("yes", "on", "1", "true", "t")
    )
    env.filters["regex_replace"] = lambda s, f, r: re.sub(f, r, str(s))
    return env


BASE = dict(
    traefik_route_name="svc",
    traefik_route_fqdn="svc.example.test",
    traefik_route_rule="Host(`svc.example.test`)",
    traefik_route_backend_url="http://10.1.3.9:8080",
    traefik_route_internal_only=True,
    traefik_route_public_hardening=True,
    traefik_route_internal_cidrs=["10.0.0.0/8", "100.64.0.0/10"],
    traefik_route_admin_cidrs=[],
    traefik_route_ratelimit_average=300,
    traefik_route_ratelimit_burst=600,
    traefik_route_forward_auth=False,
    traefik_route_backend_insecure_skip_verify=False,
    traefik_route_backend_root_ca_file="",
    traefik_route_path_prefix="",
    traefik_route_strip_prefix=False,
    traefik_route_endpoints=[],
)


def render(**over):
    v = dict(BASE)
    v.update(over)
    return _env().get_template("route.yml.j2").render(**v)


def parsed(**over):
    return yaml.safe_load(render(**over))


# --- the single-endpoint form, which thirty-one live routes use ---------------

def test_internal_route_gates_on_the_ip_allow_list():
    doc = parsed()
    assert doc["http"]["routers"]["svc"]["middlewares"] == ["svc-internal"]
    allow = doc["http"]["middlewares"]["svc-internal"]["ipAllowList"]["sourceRange"]
    assert "10.0.0.0/8" in allow and "100.64.0.0/10" in allow


def test_public_route_gets_a_rate_limit_instead():
    doc = parsed(traefik_route_internal_only=False)
    assert doc["http"]["routers"]["svc"]["middlewares"] == ["svc-ratelimit"]
    assert doc["http"]["middlewares"]["svc-ratelimit"]["rateLimit"]["average"] == 300


def test_admin_cidrs_are_appended_not_replacing():
    doc = parsed(traefik_route_admin_cidrs=["10.6.224.107/32"])
    allow = doc["http"]["middlewares"]["svc-internal"]["ipAllowList"]["sourceRange"]
    assert "10.6.224.107/32" in allow and "10.0.0.0/8" in allow


def test_forward_auth_outpost_router_is_not_itself_behind_the_auth_middleware():
    # The outpost IS the login flow; gating it on the gate locks everyone out.
    doc = parsed(traefik_route_forward_auth=True)
    assert "authentik" in doc["http"]["routers"]["svc"]["middlewares"]
    assert "authentik" not in doc["http"]["routers"]["svc-outpost"].get("middlewares", [])


def test_a_single_endpoint_route_still_renders_one_router_and_one_service():
    doc = parsed()
    assert list(doc["http"]["routers"]) == ["svc"]
    assert list(doc["http"]["services"]) == ["svc"]


# --- the multi-endpoint form --------------------------------------------------

EPS = [
    dict(name="grpc", path_prefixes=["/a.Service/", "/b.Service/"],
         backend_url="h2c://10.1.3.9:33073", priority=100),
    dict(name="api", path_prefixes=["/api"], backend_url="http://10.1.3.9:33073", priority=90),
    dict(name="ui", backend_url="http://10.1.3.9:80", priority=1),
]


def test_every_endpoint_becomes_its_own_router_and_service_in_one_file():
    doc = parsed(traefik_route_endpoints=EPS)
    assert set(doc["http"]["routers"]) == {"svc-grpc", "svc-api", "svc-ui"}
    assert set(doc["http"]["services"]) == {"svc-grpc", "svc-api", "svc-ui"}


def test_the_network_gate_reaches_every_endpoint():
    # The point of the test: a multi-endpoint route must not be a way to lose the gate.
    doc = parsed(traefik_route_endpoints=EPS)
    for name, router in doc["http"]["routers"].items():
        assert router["middlewares"] == ["svc-internal"], f"{name} is not gated"


def test_the_gate_reaches_every_endpoint_when_public_too():
    doc = parsed(traefik_route_endpoints=EPS, traefik_route_internal_only=False)
    for name, router in doc["http"]["routers"].items():
        assert router["middlewares"] == ["svc-ratelimit"], f"{name} is not throttled"


def test_several_prefixes_are_ored_a_single_one_is_bare():
    doc = parsed(traefik_route_endpoints=EPS)
    rules = {n: r["rule"] for n, r in doc["http"]["routers"].items()}
    assert rules["svc-grpc"] == (
        "Host(`svc.example.test`) && (PathPrefix(`/a.Service/`) || PathPrefix(`/b.Service/`))"
    )
    assert rules["svc-api"] == "Host(`svc.example.test`) && PathPrefix(`/api`)"
    assert rules["svc-ui"] == "Host(`svc.example.test`)"  # catch-all keeps the bare host rule


def test_the_grpc_scheme_survives_into_the_backend_url():
    # h2c:// is why NetBird could not use this role before; losing it breaks the VPN.
    doc = parsed(traefik_route_endpoints=EPS)
    assert doc["http"]["services"]["svc-grpc"]["loadBalancer"]["servers"][0]["url"].startswith("h2c://")


def test_priorities_are_explicit_so_the_catch_all_loses():
    doc = parsed(traefik_route_endpoints=EPS)
    prio = {n: r["priority"] for n, r in doc["http"]["routers"].items()}
    assert prio["svc-ui"] < prio["svc-api"] < prio["svc-grpc"]


def test_an_unwanted_gate_must_be_asked_for_explicitly():
    doc = parsed(traefik_route_endpoints=EPS, traefik_route_internal_only=False,
                 traefik_route_public_hardening=False)
    assert doc["http"].get("middlewares") is None
    for router in doc["http"]["routers"].values():
        assert "middlewares" not in router
