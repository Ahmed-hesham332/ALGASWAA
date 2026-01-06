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
    Production-grade MikroTik HotSpot + RADIUS configuration.

    ✔ RouterOS v6 / v7
    ✔ VM + Real hardware
    ✔ bridgeLocal aware
    ✔ WiFi aware
    ✔ Voucher-safe (PAP)
    """

    # ---------- TIME SYNC (VERSION-AWARE) ----------
    if routeros_version >= 7:
        ntp_cmd = """
# ---------- TIME (RouterOS v7) ----------
/system ntp client set enabled=yes
/system ntp client servers remove [find]
/system ntp client servers add address=162.159.200.1
/system ntp client servers add address=162.159.200.123
/system clock set time-zone-name=Africa/Khartoum
"""
    else:
        ntp_cmd = """
# ---------- TIME (RouterOS v6) ----------
/system ntp client set enabled=yes primary-ntp=162.159.200.1 secondary-ntp=162.159.200.123
/system clock set time-zone-name=Africa/Khartoum
"""

    config = f"""
# ==========================================
# ALGASWAA AUTO INSTALL (SMART)
# NAS-ID: {nas_identifier}
# ==========================================

# ---------- SYSTEM ID ----------
/system identity set name={nas_identifier}

# ---------- DETECT LAN BRIDGE ----------
:global LANBRIDGE ""

:if ([/interface bridge find name="bridgeLocal"] != "") do={{
    :set LANBRIDGE "bridgeLocal"
}} else={{
    :set LANBRIDGE "algaswaa-bridge"
    :if ([/interface bridge find name=$LANBRIDGE] = "") do={{
        /interface bridge add name=$LANBRIDGE
        /interface bridge port add bridge=$LANBRIDGE interface=ether2
    }}
}}

# ---------- LAN IP ----------
:if ([/ip address find interface=$LANBRIDGE] = "") do={{
    /ip address add address=10.10.10.1/24 interface=$LANBRIDGE
}}

# ---------- DHCP ----------
:if ([/ip pool find name="algaswaa_pool"] = "") do={{
    /ip pool add name=algaswaa_pool ranges=10.10.10.10-10.10.10.200
}}

:if ([/ip dhcp-server find name="algaswaa_dhcp"] = "") do={{
    /ip dhcp-server add name=algaswaa_dhcp interface=$LANBRIDGE address-pool=algaswaa_pool lease-time=1h disabled=no
}}

:if ([/ip dhcp-server network find address=10.10.10.0/24] = "") do={{
    /ip dhcp-server network add address=10.10.10.0/24 gateway=10.10.10.1 dns-server=8.8.8.8,1.1.1.1
}}

# ---------- DNS ----------
/ip dns set allow-remote-requests=yes servers=8.8.8.8,1.1.1.1

# ---------- RADIUS ----------
:if ([/radius find address={radius_ip} service=hotspot] = "") do={{
    /radius add address={radius_ip} secret={shared_secret} service=hotspot authentication-port=1812 accounting-port=1813
}}
/radius incoming set accept=yes

# ---------- HOTSPOT PROFILE ----------
:if ([/ip hotspot profile find name="algaswaa_hotspot"] = "") do={{
    /ip hotspot profile add name=algaswaa_hotspot use-radius=yes login-by=http-pap,http-chap,cookie,mac-cookie radius-interim-update=5m
    /ip hotspot user profile set [find name="algaswaa_hotspot"] shared-users=1
}}

# ---------- HOTSPOT SERVER ----------
:if ([/ip hotspot find name="algaswaa_hotspot"] = "") do={{
    /ip hotspot add name=algaswaa_hotspot interface=$LANBRIDGE profile=algaswaa_hotspot address-pool=algaswaa_pool
}}

# ---------- HOTSPOT ENABLE ----------
/ip hotspot enable algaswaa_hotspot

# ---------- NAT ----------
:if ([/ip firewall nat find chain=srcnat out-interface=ether1] = "") do={{
    /ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade
}}

# ---------- WALLED GARDEN ----------
/ip hotspot walled-garden ip remove [find]
/ip hotspot walled-garden ip add dst-address={radius_ip} protocol=tcp dst-port=80
/ip hotspot walled-garden ip add dst-address={radius_ip} protocol=tcp dst-port=443
/ip hotspot walled-garden ip add dst-address={radius_ip} protocol=tcp dst-port=8000

{ntp_cmd}

# ---------- HOTSPOT FILES ----------
/file remove [find name="hotspot/login.html"]
/file remove [find name="hotspot/status.html"]

:delay 2s

/tool fetch url=("http://{radius_ip}/radius-integration/api/install/{nas_identifier}/login/") dst-path="hotspot/login.html" mode=http keep-result=yes
/tool fetch url=("http://{radius_ip}/radius-integration/api/install/{nas_identifier}/status/") dst-path="hotspot/status.html" mode=http keep-result=yes

# ---------- CLEAN STATE ----------
/ip hotspot active remove [find]
/ip hotspot cookie remove [find]
/ip hotspot host remove [find]

:log info "ALGASWAA HOTSPOT INSTALL COMPLETE"
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
