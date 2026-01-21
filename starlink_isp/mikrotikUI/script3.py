#!/usr/bin/env python3
import pymysql.cursors
import subprocess
from datetime import datetime

# ----------------------------------------------------
# DB CONFIG (same style as your example)
# ----------------------------------------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'radius',
    'password': 'modi@2000',
    'database': 'radius',
    'cursorclass': pymysql.cursors.DictCursor,
}

COA_SECRET = "mikroConnectsecret"   # must match Mikrotik /radius incoming secret

# --- table/column names (edit if yours differ) ---
VOUCHERS_TABLE = "vouchers"
V_COL_CODE     = "voucher_number"            # voucher serial used as username in radius
V_COL_NAS      = "nas_identifier"  # voucher linked to NAS id
V_COL_USEDUP   = "status"         # 0/1
V_COL_USEDUPAT = "activated_at"      # nullable datetime

SSTP_TABLE = "nas_tunnel_map"
S_COL_NAS  = "nas_identifier"
S_COL_IP   = "tunnel_ip"

QUOTA_ATTR = "Mikrotik-Total-Limit"

def send_disconnect(tunnel_ip: str, username: str, acct_session_id: str | None, framed_ip: str | None) -> bool:
    lines = [f'User-Name = "{username}"']
    if acct_session_id:
        lines.append(f'Acct-Session-Id = "{acct_session_id}"')
    if framed_ip:
        lines.append(f"Framed-IP-Address = {framed_ip}")
    payload = "\n".join(lines) + "\n"

    cmd = ["radclient", "-x", f"{tunnel_ip}:3799", "disconnect", COA_SECRET]
    p = subprocess.run(cmd, input=payload.encode("utf-8"), capture_output=True)
    out = (p.stdout or b"").decode("utf-8", "ignore")
    ok = ("Disconnect-ACK" in out) or ("Received Disconnect-ACK" in out)
    if not ok:
        err = (p.stderr or b"").decode("utf-8", "ignore")
        print(f"[WARN] Disconnect failed for {username} via {tunnel_ip}. out={out.strip()} err={err.strip()}")
    return ok

def run_quota_enforce():
    print(f"--- CRON3 quota enforce at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

    try:
        cnx = pymysql.connect(**DB_CONFIG)
        cursor = cnx.cursor()
    except pymysql.err.OperationalError as e:
        print(f"ERROR: Could not connect to MySQL database. Details: {e}")
        return

    try:
        # 1) get vouchers that are not used up AND have a quota in radreply
        cursor.execute(f"""
            SELECT v.{V_COL_CODE} AS code,
                   v.{V_COL_NAS}  AS nas,
                   s.{S_COL_IP}   AS tunnel_ip,
                   rr.value       AS quota_bytes
            FROM {VOUCHERS_TABLE} v
            JOIN {SSTP_TABLE} s
              ON s.{S_COL_NAS} = v.{V_COL_NAS}
            JOIN radreply rr
              ON rr.username = v.{V_COL_CODE}
             AND rr.attribute = %s
            WHERE (v.{V_COL_USEDUP} = 1)
        """, (QUOTA_ATTR,))
        vouchers = cursor.fetchall()

        if not vouchers:
            print("OK: No vouchers with quota to check.")
            return

        for v in vouchers:
            code = str(v["code"])
            nas  = str(v["nas"])
            tip  = str(v["tunnel_ip"])
            try:
                quota = int(v["quota_bytes"])
            except Exception:
                continue

            # 2) total used bytes across radacct (all sessions)
            cursor.execute("""
                SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0) AS total
                FROM radacct
                WHERE username = %s
            """, (code,))
            used = int(cursor.fetchone()["total"] or 0)

            if used < quota:
                cursor.execute(f"""
                    update vouchers
                    set data = %s 
                    where voucher_number = %s
                """, (used, code))
                cnx.commit()
                continue

            # 3) find current active session (for best disconnect reliability)
            cursor.execute("""
                SELECT acctsessionid, framedipaddress
                FROM radacct
                WHERE username=%s AND acctstoptime IS NULL
                ORDER BY acctstarttime DESC
                LIMIT 1
            """, (code,))
            active = cursor.fetchone() or {}
            acctsessionid = active.get("acctsessionid")
            framedip = active.get("framedipaddress")

            # 4) disconnect active session (if any)
            ok = send_disconnect(tip, code, acctsessionid, framedip)

            # 5) reject future auth (blocks cookie re-login too)
            # cursor.execute("DELETE FROM radcheck WHERE username=%s AND attribute='Auth-Type'", (code,))
            cursor.execute("""
                INSERT INTO radcheck (username, attribute, op, value)
                VALUES (%s, 'Auth-Type', ':=', 'Reject')
            """, (code,))

            cursor.execute(f"""
                    update vouchers
                    set data = %s 
                    where voucher_number = %s
                """, (used, code))

            # 6) mark used_up in vouchers (prevents repeated CoA spam)
            cursor.execute(f"""
                UPDATE {VOUCHERS_TABLE}
                SET {V_COL_USEDUP}=2
                WHERE {V_COL_CODE}=%s
            """, (code,))

            cnx.commit()

            print(f"[QUOTA] used_up={code} used={used} quota={quota} nas={nas} tunnel={tip} disconnect_ok={ok}")

        print("OK: quota enforcement done.")

    except Exception as e:
        cnx.rollback()
        print(f"ERROR: {e}")
    finally:
        cursor.close()
        cnx.close()

if __name__ == "__main__":
    run_quota_enforce()
