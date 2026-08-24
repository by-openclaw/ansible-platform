#!/usr/bin/env python3
# ==============================================================================
# JumpServer bastion reconcile — idempotent, token-free (run via
# `manage.py shell < reconcile.py`, same model as gitlab_rbac's rails runner).
# Reads desired state from /tmp/jms_reconcile.json and the SSH key(s) from files
# it references. Prints a summary; never prints secrets. Safe to re-run.
#
# Does: (1) bastion admin user -> System Admin + bastion group,
#       (2) register assets into nodes, (3) vault the SSH key as each asset's
#       account, (4) grant the bastion group all-assets, (5) replay storage -> S3.
# ==============================================================================
import json

from orgs.models import Organization
from orgs.utils import set_current_org

set_current_org(Organization.default())

from assets.models import Host, Node, Protocol           # noqa: E402
from accounts.models import Account                       # noqa: E402
from perms.models import AssetPermission                  # noqa: E402
from perms.const import ActionChoices                     # noqa: E402
from users.models import User, UserGroup                  # noqa: E402
from rbac.models import SystemRoleBinding                 # noqa: E402
from terminal.models import ReplayStorage                 # noqa: E402

CFG = json.load(open("/tmp/jms_reconcile.json"))
PLATFORM_ID = {"Linux": 1, "Windows": 5}
SYSTEM_ADMIN_ROLE = "00000000-0000-0000-0000-000000000001"
# full action bitmask (connect|upload|download|copy|paste|delete|share)
ALL_ACTIONS = 0
for _c in ActionChoices:
    ALL_ACTIONS |= _c.value
summary = []


def load_key(path):
    with open(path) as f:
        return f.read()


# --- (1) bastion admin user -> System Admin + bastion group ------------------
admin = CFG["bastion_admin"]
u, created = User.objects.get_or_create(
    username=admin["username"],
    defaults={"name": admin["name"], "email": admin["email"], "source": "openid"},
)
# make sure a pre-existing local user is adoptable by OIDC (username match)
if u.source != "openid":
    u.source = "openid"
    u.save(update_fields=["source"])
srb, srb_created = SystemRoleBinding.objects.get_or_create(user=u, role_id=SYSTEM_ADMIN_ROLE)
summary.append(f"admin={u.username} created={created} system_admin={not srb_created or srb_created}")

grp, g_created = UserGroup.objects.get_or_create(name=CFG["bastion_group"])
if not grp.users.filter(pk=u.pk).exists():
    grp.users.add(u)
summary.append(f"group={grp.name} created={g_created} member={u.username}")

# --- (2)+(3) nodes, assets, accounts ----------------------------------------
root = Node.org_root()
node_cache = {}


def get_node(value):
    if value not in node_cache:
        res = root.get_or_create_child(value=value)
        node_cache[value] = res[0] if isinstance(res, tuple) else res
    return node_cache[value]


key_cache = {}
n_hosts = n_accounts = 0
for a in CFG["assets"]:
    node = get_node(a["node"])
    host, h_created = Host.objects.get_or_create(
        name=a["name"],
        defaults={"address": a["address"], "platform_id": PLATFORM_ID[a.get("platform", "Linux")]},
    )
    # keep address current + ensure node membership
    if host.address != a["address"]:
        host.address = a["address"]
        host.save(update_fields=["address"])
    if not host.nodes.filter(pk=node.pk).exists():
        host.nodes.add(node)
    Protocol.objects.get_or_create(
        asset=host, name=a.get("protocol", "ssh"), defaults={"port": a.get("port", 22)}
    )
    if h_created:
        n_hosts += 1
    # account (SSH key vaulted into JumpServer)
    kp = a["key_file"]
    if kp not in key_cache:
        key_cache[kp] = load_key(kp)
    acct, a_created = Account.objects.get_or_create(
        asset=host,
        username=a["account"],
        defaults={"name": a["account"], "secret_type": "ssh_key", "privileged": a.get("privileged", False)},
    )
    if a_created:
        acct.secret = key_cache[kp]
        acct.save()
        n_accounts += 1
summary.append(f"assets: +{n_hosts} new hosts, +{n_accounts} new accounts (of {len(CFG['assets'])})")

# --- (4) grant: bastion group -> whole node tree -> all accounts -------------
perm, p_created = AssetPermission.objects.get_or_create(
    name=CFG["permission_name"],
    defaults={"accounts": ["@ALL"], "protocols": ["all"], "actions": ALL_ACTIONS},
)
perm.user_groups.add(grp)
perm.nodes.add(root)
summary.append(f"permission={perm.name} created={p_created} -> group {grp.name}, all nodes")

# --- (5) replay storage -> SeaweedFS S3 -------------------------------------
s3 = CFG.get("s3")
if s3:
    meta = {
        "BUCKET": s3["bucket"],
        "ACCESS_KEY": s3["access_key"],
        "SECRET_KEY": s3["secret_key"],
        "ENDPOINT": s3["endpoint"],
        "REGION": s3.get("region", "us-east-1"),
    }
    st, s_created = ReplayStorage.objects.get_or_create(
        name=CFG["s3_storage_name"], defaults={"type": "s3", "meta": meta, "is_default": True}
    )
    if not s_created and st.meta != meta:
        st.meta = meta
        st.type = "s3"
        st.save(update_fields=["meta", "type"])
    # make it the only default
    ReplayStorage.objects.exclude(pk=st.pk).filter(is_default=True).update(is_default=False)
    if not st.is_default:
        st.is_default = True
        st.save(update_fields=["is_default"])
    summary.append(f"replay_storage={st.name} type=s3 created={s_created} default=True")

# --- (6) JumpServer feature settings (bastion) ------------------------------
# e.g. ANSIBLE_DOCKER_ENABLED=false: run asset connectivity / account tasks in
# the celery container (we deliberately don't mount docker.sock, so the default
# per-task ansible-executor Docker container can't spawn). Idempotent.
from settings.models import Setting  # noqa: E402

for _name, _val in CFG.get("settings", {}).items():
    Setting.objects.update_or_create(
        name=_name,
        defaults={"value": json.dumps(_val), "category": "terminal", "encrypted": False},
    )
if CFG.get("settings"):
    summary.append(f"settings: {', '.join(f'{k}={v}' for k, v in CFG['settings'].items())}")

print("RECONCILE_OK")
for line in summary:
    print("  -", line)
