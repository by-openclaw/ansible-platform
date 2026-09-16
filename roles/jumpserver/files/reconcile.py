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

org = Organization.default()
set_current_org(org)

from assets.models import Asset, Host, Node, Protocol    # noqa: E402
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
n_hosts = n_accounts = n_ports = n_stale = n_rekeyed = 0
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
    # set node membership to exactly the configured category (clean reorg — an
    # asset moved to a new service-type node is not left behind in the old one)
    host.nodes.set([node])
    # port/account/privilege/key follow the hardening baseline unless the asset overrides them
    D = CFG.get("asset_defaults", {})
    port = int(a.get("port", D.get("port", 22)))
    account = a.get("account", D.get("account", "root"))
    privileged = bool(a.get("privileged", D.get("privileged", False)))
    kp = a.get("key_file", D.get("key_file", "/tmp/jms_key_asset"))
    proto, _pc = Protocol.objects.get_or_create(
        asset=host, name=a.get("protocol", "ssh"), defaults={"port": port}
    )
    if proto.port != port:
        proto.port = port
        proto.save(update_fields=["port"])
        n_ports += 1
    if h_created:
        n_hosts += 1
    # account (SSH key vaulted into JumpServer)
    if kp not in key_cache:
        key_cache[kp] = load_key(kp)
    acct, a_created = Account.objects.get_or_create(
        asset=host,
        username=account,
        defaults={"name": account, "secret_type": "ssh_key", "privileged": privileged},  # pragma: allowlist secret
    )
    if a_created:
        acct.secret = key_cache[kp]
        acct.save()
        n_accounts += 1
    else:
        if acct.privileged != privileged:
            acct.privileged = privileged
            acct.save(update_fields=["privileged"])
        if (acct.secret or "") != key_cache[kp]:   # key rotated/replaced in Vault
            acct.secret = key_cache[kp]
            acct.save()
            n_rekeyed += 1
    # accounts the catalog no longer declares for this asset (e.g. root after the hardening
    # switch) cannot log in anyway: drop them so the connect dialog offers only what works
    for stale in Account.objects.filter(asset=host).exclude(username=account):
        stale.delete()
        n_stale += 1
summary.append(
    f"assets: +{n_hosts} new hosts, +{n_accounts} new accounts, {n_ports} port fixes, "
    f"-{n_stale} stale accounts, {n_rekeyed} re-keyed (of {len(CFG['assets'])})"
)

# --- (4) grant: bastion group -> whole node tree -> all accounts -------------
perm, p_created = AssetPermission.objects.get_or_create(
    name=CFG["permission_name"],
    defaults={"accounts": ["@ALL"], "protocols": ["all"], "actions": ALL_ACTIONS},
)
perm.user_groups.add(grp)
# Grant the SPECIFIC child nodes the assets live in (SVC/DMZ/…), NOT the org
# root: granting the org root puts the user in "has-all" mode, which the v4
# Workbench renders as an EMPTY tree. Child-node grants materialise per-node
# relations so assets actually show. node_cache holds every node we placed an
# asset in this run.
for _child in node_cache.values():
    perm.nodes.add(_child)
perm.nodes.remove(root)  # idempotent: undo any prior root grant
# The v4 Workbench flat listing ("All assets") reads DIRECT asset grants — node
# membership alone yields correct per-node COUNTS but an EMPTY listing (observed
# live). Grant every managed asset directly too, so the tree counts AND the flat
# listing both populate. set() is idempotent and self-heals: a newly added asset
# (e.g. OPNsense) picks up its direct grant on the next run automatically.
try:
    perm.assets.set(list(Asset.objects.all()))
except Exception as _e:  # noqa: BLE001
    summary.append(f"WARN direct-asset grant failed: {type(_e).__name__}")
# Make the Workbench reflect the grant immediately: expire AND rebuild the perm
# tree for the granted group's members. Expiring alone only marks it stale — the
# Workbench reads the BUILT tree, and the lazy rebuild doesn't reliably fire — so
# force the refresh per user here.
try:
    from perms.utils.user_perm_tree import UserPermTreeExpireUtil, UserPermTreeRefreshUtil

    _member_ids = list(grp.users.values_list("id", flat=True))
    UserPermTreeExpireUtil().expire_perm_tree_for_users_orgs(_member_ids, [org.id])
    for _uu in User.objects.filter(id__in=_member_ids):
        UserPermTreeRefreshUtil(_uu).refresh_if_need(True)
    _pt = f"rebuilt for {len(_member_ids)} user(s)"
except Exception as _e:  # noqa: BLE001
    _pt = f"tree-rebuild skipped ({type(_e).__name__})"
summary.append(f"permission={perm.name} created={p_created} -> group {grp.name}, all nodes; perm-tree {_pt}")

# --- (4b) refresh cached per-node asset counts (the tree badges) -------------
# host.nodes.set() fires the m2m signal, but the cached assets_amount can lag on
# bulk runs, showing a stale (0) badge. Recompute so the badges match the tree.
# Best-effort / idempotent — only writes the nodes whose count actually drifted.
try:
    _fixed = 0
    for _n in Node.objects.all():
        _cnt = _n.get_all_assets().count()
        if _n.assets_amount != _cnt:
            Node.objects.filter(id=_n.id).update(assets_amount=_cnt)
            _fixed += 1
    summary.append(f"node-count refresh: {_fixed} badge(s) corrected")
except Exception as _e:  # noqa: BLE001
    summary.append(f"node-count refresh skipped ({type(_e).__name__})")

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
        summary.append("replay_storage_meta updated=True")
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

# --- (7) Email (mailcow SMTP) — notifications sender ------------------------
email = CFG.get("email")
if email and email.get("smtp_host"):
    email_vals = {
        "EMAIL_HOST": email["smtp_host"],
        "EMAIL_PORT": email["smtp_port"],
        "EMAIL_HOST_USER": email["smtp_user"],
        "EMAIL_HOST_PASSWORD": email["smtp_password"],
        "EMAIL_FROM": "JumpServer <%s>" % email["smtp_user"],
        "EMAIL_USE_TLS": True,
        "EMAIL_USE_SSL": False,
        "EMAIL_PROTOCOL": "smtp",
        "EMAIL_SUBJECT_PREFIX": "[JumpServer] ",
    }
    # encrypted=False so cleaned_value reads back the raw value (Vault is the
    # source of truth for the mailbox password; JumpServer's DB is its own store).
    for _n, _v in email_vals.items():
        Setting.objects.update_or_create(
            name=_n, defaults={"value": json.dumps(_v), "category": "email", "encrypted": False}
        )
    for _r in Setting.objects.filter(name__startswith="EMAIL_"):
        try:
            _r.refresh_setting()
        except Exception:  # noqa: BLE001
            pass
    summary.append(f"email: SMTP -> {email['smtp_host']}:{email['smtp_port']} as {email['smtp_user']}")

_changed = ("created=True" in "\n".join(summary)) or ("updated=True" in "\n".join(summary))
if _changed:
    print("RECONCILE_CHANGED")
print("RECONCILE_OK")
for line in summary:
    print("  -", line)
