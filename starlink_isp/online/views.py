from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connections
from vouchers.models import Voucher
from servers.models import Server
from vouchers.utils import update_voucher_status
from datetime import timedelta

@login_required
def online_list(request):

    user = request.user

    # 1️⃣ Reseller servers
    servers = Server.objects.filter(owner=user)

    selected_server = request.GET.get("server", "all")
    search_query = request.GET.get("search", "").strip()

    # Add is_selected flag
    for s in servers:
        s.is_selected = (str(s.id) == selected_server)

    # 2️⃣ Get all voucher serials of this reseller
    valid_serials = list(
        Voucher.objects.filter(batch__reseller=user)
        .values_list("serial", flat=True)
    )

    if not valid_serials:
        return render(request, "dashboard/online/online_list.html", {
            "sessions": [],
            "servers": servers,
            "selected_server": selected_server,
            "is_all_servers": True,
            "search_query": search_query,
        })

    # 3️⃣ Base SQL query
    sql = """
        SELECT
            username,
            callingstationid,
            framedipaddress,
            acctsessiontime,
            acctinputoctets,
            acctoutputoctets,
            nasipaddress
        FROM radacct
        WHERE acctstoptime IS NULL
        AND username IN %s
    """

    params = [tuple(valid_serials)]

    # 4️⃣ Filter by server
    if selected_server != "all":
        server = servers.filter(id=selected_server).first()
        if server:
            sql += " AND nasipaddress = %s"
            params.append(server.ip_address)

    # 5️⃣ Query RADIUS DB
    cursor = connections["radius"].cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()

    # 6️⃣ Convert to structured dictionaries
    sessions = []
    for username, mac, ip, duration, down, up, nas_ip in rows:

        server_name = Server.objects.filter(ip_address=nas_ip, owner=user).first()
        server_name = server_name.name if server_name else nas_ip
    
        # Search filter
        if search_query:
            if search_query not in username and search_query not in (mac or ""):
                continue

        sessions.append({
            "serial": username,
            "mac": mac,
            "ip": ip,
            "duration": str(timedelta(seconds=duration)) if duration else "—",
            "download": round((down or 0) / (1024 * 1024), 2),
            "upload": round((up or 0) / (1024 * 1024), 2),
            "server_ip": nas_ip,
            "server_name": server_name,
            "server_ip": nas_ip,
            "server_name": server_name,
        })

    # 7️⃣ Attach Voucher Usage Info
    if sessions:
        active_serials = [s["serial"] for s in sessions]
        vouchers_map = {
            v.serial: v.usage_mb 
            for v in Voucher.objects.filter(serial__in=active_serials)
        }
        for s in sessions:
            s["usage_mb"] = vouchers_map.get(s["serial"], 0)

    return render(request, "dashboard/online/online_list.html", {
        "sessions": sessions,
        "servers": servers,
        "selected_server": selected_server,
        "is_all_servers": (selected_server == "all"),
        "search_query": search_query,
    })
