from django.db import connections
from django.utils import timezone
from vouchers.models import Voucher

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
        shared_secret, 
        radius_ip, 
        login_html=None, 
        status_html=None,
        tech_support_name="Technical Support",
        tech_support_phone="0000000000"
    ):
    
    config = f"""
# ===============================
# RADIUS & HOTSPOT CONFIG WIZARD
# ===============================

# 1. Configure Radius Client
/radius add address={radius_ip} secret={shared_secret} service=hotspot authentication-port=1812 accounting-port=1813
/radius incoming set accept=yes

# 2. Configure Hotspot Profile
/ip hotspot profile set [find] use-radius=yes login-by=http-chap,cookie,mac-cookie 

# 3. Configure NTP (Recommended for Expiration to work)
/system ntp client set enabled=yes primary-ntp=162.159.200.1 secondary-ntp=162.159.200.123

# 4. Walled Garden (Optional basics)
/ip hotspot walled-garden ip add dst-address=72.62.26.238 protocol=tcp dst-port=8000
"""

    # Helper to escape string for MikroTik script
    def output_file_script(filename, content):
        if not content:
            return ""
        
        # Replace placeholders
        content = content.replace("{{ tech_support_name }}", tech_support_name)
        content = content.replace("{{ tech_support_phone }}", tech_support_phone)
        
        # Escape double quotes for MikroTik string
        escaped_content = content.replace('"', '\\"')
        
        return f"""
# Updating {filename}
/file set [find name="hotspot/{filename}"] contents="{escaped_content}"
"""

    if login_html:
        config += output_file_script("login.html", login_html)
        
    if status_html:
        config += output_file_script("status.html", status_html)

    config += """
# ===============================
# DONE
# ===============================
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

    return remaining_seconds

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
