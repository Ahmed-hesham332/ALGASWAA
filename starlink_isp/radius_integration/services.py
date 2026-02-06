from django.db import connections
from django.utils import timezone

RADIUS_SECRET = "mikroConnectsecret"

def radius_add_user(serial, offer, token):
    cursor = connections["radius"].cursor()

    # 1️⃣ Calculate Session Timeout 
    if offer.duration_type == "minutes":
        duration_seconds = offer.duration_value * 60
    elif offer.duration_type == "hours":
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
        if offer.quota_type == "MB":
            quota_bytes = offer.quota_amount * 1024 * 1024
        else:
            # Default to GB ("fixed")
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
        INSERT INTO vouchers (voucher_number, duration_seconds, status, nas_identifier)
        VALUES (%s, %s, %s, %s)
    """, [serial, duration_seconds, 0, token])
        
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

# ---------- DNS ----------
/ip dns set allow-remote-requests=yes servers=8.8.8.8,1.1.1.1

# ---------- RADIUS ----------
:if ([/radius find address={radius_ip} service=hotspot] = "") do={{
    /radius add address={radius_ip} secret={shared_secret} service=hotspot authentication-port=1812 accounting-port=1813
    /radius add address=172.26.0.1 secret="mikroConnectsecret" service=hotspot authentication-port=1812 accounting-port=1813
}}
/radius incoming set accept=yes port=3799

# ---------- HOTSPOT PROFILE ----------
/ip hotspot profile set [find] use-radius=yes login-by=http-pap,http-chap,mac-cookie radius-interim-update=1m
/ip hotspot user profile set [find] shared-users=1

# ---------- NAT ----------
:if ([/ip firewall nat find chain=srcnat out-interface=ether1] = "") do={{
    /ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade
}}

# ---------- WALLED GARDEN ----------
/ip hotspot walled-garden ip remove [find]
/ip hotspot walled-garden ip add dst-address={radius_ip} protocol=tcp dst-port=80
/ip hotspot walled-garden ip add dst-address={radius_ip} protocol=tcp dst-port=443
/ip hotspot walled-garden ip add dst-address={radius_ip} protocol=tcp dst-port=8000
# captive check
/ip hotspot walled-garden remove [find comment="captive-check"]
# ---------- Apple (iOS / macOS) ----------
/ip hotspot walled-garden add action=allow dst-host=captive.apple.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=www.apple.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=apple.com comment="captive-check"
# ---------- Google (Android / ChromeOS) ----------
/ip hotspot walled-garden add action=allow dst-host=connectivitycheck.gstatic.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=www.gstatic.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=clients3.google.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=clients.google.com comment="captive-check"
# ---------- Microsoft (Windows) ----------
/ip hotspot walled-garden add action=allow dst-host=www.msftconnecttest.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=msftconnecttest.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=www.msftncsi.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=msftncsi.com comment="captive-check"
# ---------- Samsung ----------
/ip hotspot walled-garden add action=allow dst-host=connectivity.samsung.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=conn.samsungapps.com comment="captive-check"
# ---------- Huawei / Honor ----------
/ip hotspot walled-garden add action=allow dst-host=connectivitycheck.platform.hicloud.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=connectivitycheck.hicloud.com comment="captive-check"
# ---------- Firefox Captive Portal ----------
/ip hotspot walled-garden add action=allow dst-host=detectportal.firefox.com comment="captive-check"
/ip hotspot walled-garden add action=allow dst-host=detectionportal.firefox.com comment="captive-check"

{ntp_cmd}

# ---------- HOTSPOT FILES ----------
/file remove [find name="hotspot/login.html"]
/file remove [find name="hotspot/status.html"]


:delay 2s

/tool fetch url=("http://{radius_ip}/radius-integration/api/install/{nas_identifier}/login/") dst-path="hotspot/login.html" mode=http keep-result=yes
/tool fetch url=("http://{radius_ip}/radius-integration/api/install/{nas_identifier}/status/") dst-path="hotspot/status.html" mode=http keep-result=yes

# ---------- ALGASWAA MANAGEMENT TUNNEL (SSTP) ----------

# Create SSTP client if not exists
:if ([:len [/interface sstp-client find name="algaswaa-sstp"]] = 0) do={{
    /interface sstp-client add name=algaswaa-sstp connect-to={radius_ip} port=443 user={nas_identifier} password={nas_identifier} profile=default-encryption authentication=pap,chap verify-server-certificate=no add-default-route=no disabled=no
}} else={{
    /interface sstp-client set [find name="algaswaa-sstp"] connect-to={radius_ip} port=443 user={nas_identifier} password={nas_identifier} profile=default-encryption authentication=pap,chap verify-server-certificate=no add-default-route=no disabled=no
}}

# Lock management services to management subnet
/ip service set api disabled=no address=172.26.0.0/16
/ip service set winbox address=172.26.0.0/16
/interface sstp-client enable algaswaa-sstp

# Allow CoA packets from VPS (adjust if your firewall differs)
/ip firewall filter add chain=input action=accept protocol=udp dst-port=3799 src-address=172.26.0.1 comment="ALGASWAA CoA"

# add management user
/user group add name=algaswaa-policy policy=read,write,policy,test,api,winbox,reboot,!password,!sniff,!sensitive
/user add name={nas_identifier} password={nas_identifier} group=algaswaa-policy comment="ALGASWAA MANAGED – DO NOT DELETE"


# ---------- HEARTBEAT SCHEDULER ----------
/system scheduler remove [find name="algaswaa-heartbeat"]
/tool fetch url=("http://{radius_ip}/radius-integration/api/heartbeat/{nas_identifier}/") keep-result=no
/system scheduler add name=algaswaa-heartbeat interval=1m on-event="/tool fetch url=http://{radius_ip}/radius-integration/api/heartbeat/{nas_identifier}/ keep-result=no"
/system scheduler add interval=2m name=smart_fix_mac on-event="/ip hotspot host remove [find authorized=no]"

# ---------- CLEAN STATE ----------
/ip hotspot active remove [find]
/ip hotspot cookie remove [find]
/ip hotspot host remove [find]

:log info "ALGASWAA HOTSPOT INSTALL COMPLETE"
"""

    return config

def add_tunnel_client(hostname, tunnel_ip):
    conn = connections["radius"]
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO nas_tunnel_map (nas_identifier, tunnel_ip)
        VALUES (%s, %s)
    """, [hostname, tunnel_ip])

    conn.commit()
    cursor.close()

def remove_tunnel_client(hostname, tunnel_ip):
    conn = connections["radius"]
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM nas_tunnel_map 
        WHERE nas_identifier = %s AND tunnel_ip = %s
    """, [hostname, tunnel_ip])

    conn.commit()
    cursor.close()

def add_radius_client(nasname, shortname, secret):
    conn = connections["radius"]
    cursor = conn.cursor()

    # 1️⃣ Check if NAS Shortname already exists (Unique Identifier)
    cursor.execute("SELECT id FROM nas WHERE shortname = %s", [shortname])
    existing = cursor.fetchone()

    if existing:
        # Update existing record
        cursor.execute("""
            UPDATE nas 
            SET nasname = %s, secret = %s
            WHERE shortname = %s
        """, [nasname, secret, shortname])
    else:
        # Insert New
        cursor.execute("""
            INSERT INTO nas (nasname, shortname, type, secret)
            VALUES (%s, %s, 'mikrotik', %s)
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
    # """
    # Delete NAS client from FreeRADIUS by IP address.
    # """
    # cursor = connections['radius'].cursor()
    # cursor.execute("DELETE FROM nas WHERE shortname = %s", [token])
    # cursor.close()
    pass

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
