# Provision a PER-USER shared-cluster server for every pgAdmin user, each owned by
# that user, with the passexec command — because pgAdmin runs passexec ONLY for the
# server's OWNER, so a single SHARED server can never connect passwordless for
# non-owner SSO users (they get a "Connect to Server" password prompt / HTTP 428).
# Giving each user their own owned entry makes passexec fire for everyone.
#
# pgAdmin's state lives on the shared PostgreSQL: the connection is the SAME URI the
# container runs with (PGADMIN_CONFIG_CONFIG_DATABASE_URI, a Python string literal).
# Idempotent: matches an existing entry by (user_id, name); creates or converges only
# when something drifts. Reads its config from /tmp/pg_provision.json.
import ast, json, os, sys

import psycopg

cfg = json.load(open("/tmp/pg_provision.json"))
uri = ast.literal_eval(os.environ["PGADMIN_CONFIG_CONFIG_DATABASE_URI"])
conn_params = json.dumps({"sslmode": cfg["sslmode"]})
changed = 0

with psycopg.connect(uri) as c:
    for (uid,) in c.execute('select id from "user"').fetchall():
        desired = dict(
            user_id=uid, name=cfg["name"], host=cfg["host"], port=int(cfg["port"]),
            maintenance_db=cfg["maintenance_db"], username=cfg["username"],
            connection_params=conn_params, db_res_type="databases",
            shared=False, save_password=1, passexec_cmd=cfg["passexec"], password=None,
            comment=cfg.get("comment", ""),
        )
        ex = c.execute(
            "select id, servergroup_id, host, port, username, maintenance_db, passexec_cmd, shared "
            "from server where user_id = %s and name = %s", (uid, cfg["name"])).fetchone()
        if ex:
            desired["servergroup_id"] = ex[1]   # keep it where the user has it
            drift = (ex[2], ex[3], ex[4], ex[5], ex[6], bool(ex[7])) != (
                cfg["host"], int(cfg["port"]), cfg["username"], cfg["maintenance_db"], cfg["passexec"], False)
            if drift:
                desired["id"] = ex[0]
                c.execute("update server set " + ", ".join(f"{k} = %({k})s" for k in desired if k != "id")
                          + " where id = %(id)s", desired)
                changed += 1
        else:
            # new server → the user's default (first) group, creating one if they have none
            g = c.execute("select id from servergroup where user_id = %s order by id limit 1", (uid,)).fetchone()
            if not g:
                g = c.execute("insert into servergroup (user_id, name) values (%s, 'Servers') returning id",
                              (uid,)).fetchone()
            desired["servergroup_id"] = g[0]
            c.execute("insert into server (" + ", ".join(desired) + ") values ("
                      + ", ".join(f"%({k})s" for k in desired) + ")", desired)
            changed += 1

sys.stdout.write(f"CHANGED={changed}")
