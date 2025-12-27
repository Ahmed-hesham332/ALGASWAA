from django.db import connections
from django.utils import timezone

RADIUS_SECRET = "mikroConnectsecret"

def radius_add_user(serial, offer, token):
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
        VALUES (%s, 'NAS-Identifier', '==', %s)
    """, [serial, token])

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
    shared_secret: str,
    radius_ip: str,
    nas_identifier: str,
    routeros_version: int = 7,   # 6 or 7
):
    """
    Auto-generated MikroTik Hotspot + RADIUS configuration.

    - RouterOS v6 / v7 supported
    - Safe (no WAN/interface guessing)
    - Uses NAS-Identifier (important for NAT / Starlink)
    """

    identity_cmd = f"""
/system identity set name={nas_identifier}
"""
    
    # ---------- RADIUS ----------
    radius_cmd = f"""
/radius add address={radius_ip} secret={shared_secret} service=hotspot authentication-port=1812 accounting-port=1813 
/radius incoming set accept=yes
"""

    # ---------- LAN BRIDGE ----------
    lan_cmd = """
# Create dedicated LAN bridge
/interface bridge add name=algaswaa-bridge 
/interface bridge port add bridge=algaswaa-bridge interface=ether2

# Assign LAN IP
/ip address add address=10.10.10.1/24 interface=algaswaa-bridge 

# DHCP pool
/ip pool add name=algaswaa_pool ranges=10.10.10.10-10.10.10.200

# DHCP server
/ip dhcp-server add name=algaswaa_dhcp interface=algaswaa-bridge address-pool=algaswaa_pool lease-time=1h disabled=no

# DHCP network
/ip dhcp-server network add address=10.10.10.0/24 gateway=10.10.10.1 dns-server=8.8.8.8,1.1.1.1

/ip dns set allow-remote-requests=yes servers=8.8.8.8,1.1.1.1
"""

    # ---------- HOTSPOT ----------
    hotspot_cmd = """
# Hotspot profile
/ip hotspot profile add name=algaswaa_hotspot use-radius=yes login-by=http-chap,cookie,mac-cookie radius-interim-update=5m

# Hotspot server
/ip hotspot add name=algaswaa_hotspot interface=algaswaa-bridge profile=algaswaa_hotspot address-pool=algaswaa_pool

# Hotspot shared users
/ip hotspot profile set algaswaa_hotspot shared-users=1

# Hotspot enable
/ip hotspot enable algaswaa_hotspot
"""

    # ---------- TIME SYNC ----------
    if routeros_version >= 7:
        ntp_cmd = """
/system ntp client set enabled=yes
/system ntp client servers add address=162.159.200.1
/system ntp client servers add address=162.159.200.123
/system clock set time-zone-name=Africa/Khartoum
    """
    else:
        ntp_cmd = """
/system ntp client set enabled=yes primary-ntp=162.159.200.1 secondary-ntp=162.159.200.123
/system clock set time-zone-name=Africa/Khartoum
    """

    # ---------- WALLED GARDEN + NAT ----------
    walled_garden_cmd = """
/ip hotspot walled-garden ip add dst-address=72.62.26.238 protocol=tcp dst-port=80
/ip hotspot walled-garden ip add dst-address=72.62.26.238 protocol=tcp dst-port=443
/ip hotspot walled-garden ip add dst-address=72.62.26.238 protocol=tcp dst-port=8000
/ip firewall nat add chain=srcnat src-address=10.10.10.0/24 out-interface=ether1 action=masquerade
"""

    # ---------- FINAL ----------
    config = f"""
# ==========================================
# ALGASWAA AUTO INSTALL
# NAS-ID: {nas_identifier}
# ==========================================

# 1️⃣ RADIUS
{identity_cmd}
{radius_cmd}

# 2️⃣ LAN + DHCP
{lan_cmd}

# 3️⃣ HOTSPOT
{hotspot_cmd}

# 4️⃣ TIME SYNC
{ntp_cmd}

# 5️⃣ WALLED GARDEN + NAT
{walled_garden_cmd}
"""

    # ---------- HTML ----------
    # Dynamic fetch from API
    files_cmd = f"""
# 5️⃣ FILES SETUP
/file remove [find name="hotspot/login.html"]
/file remove [find name="hotspot/status.html"]

:delay 2s

/tool fetch url="http://{radius_ip}/radius-integration/api/install/{nas_identifier}/login/" dst-path="hotspot/login.html" mode=http keep-result=yes
/tool fetch url="http://{radius_ip}/radius-integration/api/install/{nas_identifier}/status/" dst-path="hotspot/status.html" mode=http keep-result=yes
"""

    config += files_cmd

    config += """
# ==========================================
# INSTALL COMPLETE ✅
# Add ports or Wi-Fi to bridge:
# /interface bridge port add bridge=algaswaa-bridge interface=etherX
# ==========================================
"""

    return config


def add_radius_client(nasname, shortname, secret):
    conn = connections["radius"]
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO nas (nasname, shortname, type, secret)
        VALUES (%s, %s, 'mikrotik', %s)
        ON DUPLICATE KEY UPDATE secret = VALUES(secret);
    """, [nasname, shortname, secret])

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

def radius_delete_client(token):
    """
    Delete NAS client from FreeRADIUS by IP address.
    """
    cursor = connections['radius'].cursor()
    cursor.execute("DELETE FROM nas WHERE shortname = %s", [token])
    cursor.close()

def voucher_radius_delete(username):
    cursor = connections['radius'].cursor()
    cursor.execute("DELETE FROM radcheck WHERE username = %s", [username])
    cursor.execute("DELETE FROM radreply WHERE username = %s", [username])
    cursor.execute("DELETE FROM vouchers WHERE voucher_number = %s", [username])
    cursor.close()

def radius_suspend_unused_vouchers(reseller):
    """
    Suspend ONLY unused vouchers for a reseller.
    Used vouchers keep working.
    """

    cursor = connections["radius"].cursor()

    from vouchers.models import Voucher
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
