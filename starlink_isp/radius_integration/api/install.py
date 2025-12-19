import os
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from servers.models import Server
from ..services import generate_mikrotik_config, add_radius_client, RADIUS_SECRET
from django.contrib.auth import get_user_model
from ..utils import get_client_ip

def mikrotik_install(request, token, version):
    try:
        # Token format: "{owner_id}_{server_id}"
        owner_id, server_id = token.split('_')
    except ValueError:
        raise Http404("Invalid token format")

    User = get_user_model()

    server = get_object_or_404(
        Server,
        id=server_id,
        owner_id=owner_id
    )

    # ✅ FIX: Get REAL MikroTik WAN IP
    mikrotik_ip = get_client_ip(request)

    # if not mikrotik_ip or mikrotik_ip.startswith("127."):
    #     raise Http404("Invalid MikroTik IP detected")

    # Update server WAN IP
    server.ip_address = mikrotik_ip
    server.save(update_fields=["ip_address"])

    # Ensure NAS exists (NAS-ID = token)
    add_radius_client(
        hostname=mikrotik_ip,      # nasname (IP)
        shortname=token,           # NAS-Identifier (UNIQUE)
        secret=RADIUS_SECRET
    )

    # RouterOS version parsing
    try:
        ver_int = int(version.lstrip("v"))
    except Exception:
        ver_int = 7

    # Load MikroTik UI templates
    login_html = None
    status_html = None

    login_html_path = os.path.join(settings.BASE_DIR, "mikrotikUI", "login.html")
    status_html_path = os.path.join(settings.BASE_DIR, "mikrotikUI", "status.html")

    if os.path.exists(login_html_path):
        with open(login_html_path, "r", encoding="utf-8") as f:
            login_html = f.read()

    if os.path.exists(status_html_path):
        with open(status_html_path, "r", encoding="utf-8") as f:
            status_html = f.read()

    # Tech Support Info
    ts_name = "Support"
    ts_phone = "0000000000"

    if server.owner.tech_support_assigned:
        ts_name = server.owner.tech_support_assigned.name
        ts_phone = server.owner.tech_support_assigned.phone

    # Generate MikroTik config
    config_text = generate_mikrotik_config(
        shared_secret=RADIUS_SECRET,
        radius_ip="72.62.26.238",
        nas_identifier=token,
        mikrotik_wan_ip=mikrotik_ip,
        routeros_version=ver_int,
        login_html=login_html,
        status_html=status_html,
        tech_support_name=ts_name,
        tech_support_phone=ts_phone
    )

    return HttpResponse(config_text, content_type="text/plain; charset=utf-8")
