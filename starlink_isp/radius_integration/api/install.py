import os
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from servers.models import Server
from ..services import generate_mikrotik_config, add_radius_client, RADIUS_SECRET
from django.contrib.auth import get_user_model

def mikrotik_install(request, token, version):
    try:
        # Token format: "{owner_id}_{server_id}"
        owner_id, server_id = token.split('_')
    except ValueError:
        raise Http404("Invalid token format")

    User = get_user_model()
    # Get server ensuring it belongs to the owner from the token
    server = get_object_or_404(Server, id=server_id, owner_id=owner_id)
    
    # Get IP from request
    mikrotik_ip = request.META.get("REMOTE_ADDR")

    # Ensure RADIUS client exists/updated with new IP
    add_radius_client(
        ip=mikrotik_ip,
        secret=RADIUS_SECRET,
        shortname=token
    )
    
    # Generate Config
    try:
        ver_int = int(version)
    except ValueError:
        if version.startswith('v'):
             version = version[1:]
        try:
            ver_int = int(version)
        except:
             ver_int = 7

    # Load HTML Templates from 'mikrotikUI' folder
    login_html_path = os.path.join(settings.BASE_DIR, 'mikrotikUI', 'login.html')
    status_html_path = os.path.join(settings.BASE_DIR, 'mikrotikUI', 'status.html')

    try:
        with open(login_html_path, 'r', encoding='utf-8') as f:
            login_html = f.read()
    except FileNotFoundError:
        login_html = None

    try:
        with open(status_html_path, 'r', encoding='utf-8') as f:
            status_html = f.read()
    except FileNotFoundError:
        status_html = None

    config_text = generate_mikrotik_config(
        shared_secret=RADIUS_SECRET,
        radius_ip="72.62.26.238", 
        nas_identifier=token, 
        mikrotik_wan_ip=mikrotik_ip,
        routeros_version=ver_int,
        login_html=login_html,
        status_html=status_html,
        tech_support_name="Support",
        tech_support_phone="0000000000"
    )

    return HttpResponse(config_text, content_type="text/plain; charset=utf-8")
