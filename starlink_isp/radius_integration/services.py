from django.db import connections
from django.utils import timezone
from vouchers.models import Voucher

RADIUS_SECRET = "mikroConnectsecret"

def radius_add_user(serial, offer, ip_address):
    cursor = connections["radius"].cursor()

    # 1️⃣ Calculate Session Timeout 
    if offer.duration_type == "hours":
        duration_seconds = offer.duration_value * 3600
    elif offer.duration_type == "days":
        duration_seconds = offer.duration_value * 86400
    elif offer.duration_type == "months":
        duration_seconds = offer.duration_value * 30 * 86400
    else:
        duration_seconds = 0    


    # Insert NAS IP Address 
    cursor.execute("""
        INSERT INTO radcheck (username, attribute, op, value)
        VALUES (%s, 'NAS-IP-Address', '==', %s)
    """, [serial, ip_address])

    # Insert password 
    cursor.execute("""
        INSERT INTO radcheck (username, attribute, op, value)
        VALUES (%s, 'Cleartext-Password', ':=', %s)
    """, [serial, serial])

    # Insert speed settings 
    if offer.unlimited_speed:
        rate_limit = "0/0"
    else:
        rate_limit = f"{offer.download_speed}k/{offer.upload_speed}k"

    cursor.execute("""
        INSERT INTO radreply (username, attribute, op, value)
        VALUES (%s, 'Mikrotik-Rate-Limit', ':=', %s)
    """, [serial, rate_limit])

    # Insert quota
    if offer.quota_type != "none":
       
        quota_bytes = offer.quota_amount * 1024 * 1024 * 1024 
        cursor.execute("""
            INSERT INTO radreply (username, attribute, op, value)
            VALUES (%s, 'Mikrotik-Total-Limit', ':=', %s)
        """, [serial, quota_bytes])

    # Insert Session Timeout
    cursor.execute("""
        INSERT INTO radreply (username, attribute, op, value)
        VALUES (%s, 'Session-Timeout', ':=', %s)
    """, [serial, duration_seconds])

    cursor.execute("""
        INSERT INTO vouchers (voucher_number, duration_seconds, status)
        VALUES (%s, %s, %s)
    """, [serial, duration_seconds, 0])
        
    cursor.close()
    
def add_radius_expiration(username, expires_at):
    """
    Writes Expiration attribute into radcheck table for a user.
    If the attribute already exists, it updates it.
    """

    if expires_at is None:
        return False

    expires_at = expires_at.astimezone(timezone.get_current_timezone())
    expiration_str = expires_at.strftime("%d %b %Y %H:%M")

    cursor = connections["radius"].cursor()

    cursor.execute("""
        INSERT INTO radcheck (username, attribute, op, value)
        VALUES (%s, 'Expiration', ':=', %s)
        ON DUPLICATE KEY UPDATE value = VALUES(value)
    """, [username, expiration_str])

    cursor.close()

    return True

def generate_mikrotik_config(
    *,
    shared_secret: str = RADIUS_SECRET,
    radius_ip: str,
    nas_identifier: str,
    mikrotik_wan_ip: str | None = None,
    routeros_version: int = 7,   # 6 or 7
    login_html: str | None = None,
    status_html: str | None = None,
    tech_support_name: str = "Technical Support",
    tech_support_phone: str = "0000000000",
):
    """
    Generates a MikroTik Hotspot + RADIUS configuration script.

    - Supports RouterOS v6 and v7
    - Uses NAS-Identifier (required for NAT / Starlink)
    - Uses RADIUS for Hotspot authentication
    """

    # ---------- RADIUS BASE ----------
    radius_cmd = f"""
/radius add address={radius_ip} secret={shared_secret} service=hotspot authentication-port=1812 accounting-port=1813 nas-identifier={nas_identifier}
"""

    # src-address exists only in v7+
    if routeros_version >= 7 and mikrotik_wan_ip:
        radius_cmd = radius_cmd.replace(
            "nas-identifier",
            f"src-address={mikrotik_wan_ip} \\\n nas-identifier"
        )

    # incoming exists only in v6
    incoming_cmd = ""
    if routeros_version == 6:
        incoming_cmd = "/radius incoming set accept=yes\n"

    # ---------- HOTSPOT PROFILE ----------
    hotspot_cmd = """
/ip hotspot profile add name=radius_hotspot use-radius=yes login-by=http-chap,cookie,mac-cookie radius-interim-update=5m
/ip hotspot set [find] profile=radius_hotspot
"""

    # ---------- TIME SYNC (CRITICAL) ----------
    ntp_cmd = """
/system ntp client set enabled=yes primary-ntp=162.159.200.1 secondary-ntp=162.159.200.123
"""

    # ---------- WALLED GARDEN ----------
    walled_garden_cmd = """
/ip hotspot walled-garden ip add dst-address=72.62.26.238 protocol=tcp dst-port=80
/ip hotspot walled-garden ip add dst-address=72.62.26.238 protocol=tcp dst-port=443
"""

    # ---------- HTML FILE HANDLER ----------
    def output_file_script(filename: str, content: str | None):
        if not content:
            return ""

        content = content.replace("{{ tech_support_name }}", tech_support_name)
        content = content.replace("{{ tech_support_phone }}", tech_support_phone)

        # Escape for MikroTik
        escaped = (
            content
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )

        return f"""
/file set [find name="hotspot/{filename}"] contents="{escaped}"
"""

    # ---------- FINAL CONFIG ----------
    config = f"""
# ==========================================
# AUTO GENERATED MIKROTIK CONFIG
# NAS-ID: {nas_identifier}
# ==========================================

# 1️⃣ RADIUS CONFIG
{radius_cmd}
{incoming_cmd}

# 2️⃣ HOTSPOT PROFILE
{hotspot_cmd}

# 3️⃣ TIME SYNC (MANDATORY)
{ntp_cmd}

# 4️⃣ WALLED GARDEN
{walled_garden_cmd}
"""

    if login_html:
        config += output_file_script("login.html", login_html)

    if status_html:
        config += output_file_script("status.html", status_html)

    config += """
# ==========================================
# CONFIG COMPLETE ✅
# ==========================================
"""

    return config


def add_radius_client(ip, secret, shortname):
    conn = connections["radius"]
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO nas (nasname, shortname, type, secret)
        VALUES (%s, %s, 'mikrotik', %s)
        ON DUPLICATE KEY UPDATE secret = VALUES(secret);
    """, [ip, shortname, secret])

    conn.commit()
    cursor.close()

def get_voucher_status(username):
    cursor = connections['radius'].cursor()
    
    cursor.execute("""
        SELECT acctstarttime, acctstoptime, framedipaddress, callingstationid,
               acctinputoctets, acctoutputoctets
        FROM radacct
        WHERE username = %s
        ORDER BY acctstarttime DESC
        LIMIT 1;
    """, [username])

    row = cursor.fetchone()
    if not row:
        return {"used": False, "active": False}

    acctstart, acctstop, ip, mac, in_bytes, out_bytes = row

    return {
        "used": True,
        "active": acctstop is None,
        "ip": ip,
        "mac": mac,
        "usage_mb": round((in_bytes + out_bytes) / (1024*1024), 2),
        "activated_at": acctstart,
        "ended_at": acctstop,
    }
    cursor.close()

def radius_delete_client(ip):
    """
    Delete NAS client from FreeRADIUS by IP address.
    """
    cursor = connections['radius'].cursor()
    cursor.execute("DELETE FROM nas WHERE nasname = %s", [ip])
    cursor.close()

def voucher_radius_delete(username):
    cursor = connections['radius'].cursor()
    cursor.execute("DELETE FROM radcheck WHERE username = %s", [username])
    cursor.execute("DELETE FROM radreply WHERE username = %s", [username])
    cursor.execute("DELETE FROM vouchers WHERE serial = %s", [username])
    cursor.close()

def radius_suspend_unused_vouchers(reseller):
    """
    Suspend ONLY unused vouchers for a reseller.
    Used vouchers keep working.
    """

    cursor = connections["radius"].cursor()

    unused_serials = Voucher.objects.filter(
        batch__reseller=reseller,
        is_used="unused"
    ).values_list("serial", flat=True)

    if not unused_serials:
        return

    # 1️⃣ Remove Cleartext-Password → block login
    cursor.execute("""
        DELETE FROM radcheck
        WHERE username IN %s
        AND attribute = 'Cleartext-Password'
    """, [tuple(unused_serials)])

    # 2️⃣ Add suspension message
    for serial in unused_serials:
        cursor.execute("""
            INSERT INTO radcheck (username, attribute, op, value)
            VALUES (%s, 'Reply-Message', ':=', 'NETWORK_SUSPENDED')
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        """, [serial])

    cursor.close()


def radius_unsuspend_unused_vouchers(reseller):
    """
    Restore ONLY unused vouchers for a reseller.
    """

    from vouchers.models import Voucher
    cursor = connections["radius"].cursor()

    unused_serials = Voucher.objects.filter(
        batch__reseller=reseller,
        is_used="unused"
    ).values_list("serial", flat=True)

    if not unused_serials:
        return

    # 1️⃣ Remove suspension message
    cursor.execute("""
        DELETE FROM radcheck
        WHERE username IN %s
        AND attribute = 'Reply-Message'
    """, [tuple(unused_serials)])

    # 2️⃣ Restore Cleartext-Password
    for serial in unused_serials:
        cursor.execute("""
            INSERT INTO radcheck (username, attribute, op, value)
            VALUES (%s, 'Cleartext-Password', ':=', %s)
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        """, [serial, serial])

    cursor.close()
