# Provision a PER-USER "BY-RESEARCH PostgreSQL" server for every pgAdmin user, each
# owned by that user, with the passexec command — because pgAdmin runs passexec ONLY
# for the server's OWNER, so a single SHARED server can never connect passwordless
# for non-owner SSO users (they get a "Connect to Server" password prompt / HTTP 428).
# Giving each user their own owned entry makes passexec fire for everyone.
#
# Idempotent: matches an existing entry by (user_id, name); creates or converges only
# when something drifts. Also un-shares any legacy shared copy of the same name.
# Reads its config from /tmp/pg_provision.json (staged by the pgadmin role).
import sqlite3, json, sys

cfg = json.load(open("/tmp/pg_provision.json"))
c = sqlite3.connect("/var/lib/pgadmin/pgadmin4.db")
conn_params = json.dumps({"sslmode": cfg["sslmode"]})
changed = 0

for (uid,) in c.execute("select id from user").fetchall():
    desired = dict(
        user_id=uid, name=cfg["name"], host=cfg["host"], port=int(cfg["port"]),
        maintenance_db=cfg["maintenance_db"], username=cfg["username"],
        connection_params=conn_params, db_res_type="databases",
        shared=0, save_password=1, passexec_cmd=cfg["passexec"], password=None,
        comment=cfg.get("comment", ""),
    )
    ex = c.execute(
        "select id,servergroup_id,host,port,username,maintenance_db,passexec_cmd,shared "
        "from server where user_id=? and name=?", (uid, cfg["name"])).fetchone()
    if ex:
        desired["servergroup_id"] = ex[1]   # keep it where the user has it
        drift = (ex[2], ex[3], ex[4], ex[5], ex[6], ex[7]) != (
            cfg["host"], int(cfg["port"]), cfg["username"], cfg["maintenance_db"], cfg["passexec"], 0)
        if drift:
            desired["id"] = ex[0]
            c.execute("update server set " + ",".join(f"{k}=:{k}" for k in desired if k != "id")
                      + " where id=:id", desired)
            changed += 1
    else:
        # new server → the user's default (first) group, creating one if they have none
        g = c.execute("select id from servergroup where user_id=? order by id limit 1", (uid,)).fetchone()
        if not g:
            c.execute("insert into servergroup (user_id,name) values (?, 'Servers')", (uid,))
            g = (c.lastrowid,)
        desired["servergroup_id"] = g[0]
        c.execute("insert into server (" + ",".join(desired) + ") values ("
                  + ",".join(f":{k}" for k in desired) + ")", desired)
        changed += 1

c.commit()
sys.stdout.write(f"CHANGED={changed}")
