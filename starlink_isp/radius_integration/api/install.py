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
    # verify owner exists (optional but good sanity check)
    # owner = get_object_or_404(User, id=owner_id) 

    # Get server ensuring it belongs to the owner from the token
    server = get_object_or_404(Server, id=server_id, owner_id=owner_id)
    
    # Get IP from request
    mikrotik_ip = request.META.get("REMOTE_ADDR")

    # Update server IP if needed? logic wasn't explicitly requested but often useful.
    # The snippet "mikrotik_ip = request.META.get('REMOTE_ADDR')" implies we use the caller's IP.
    
    # Ensure RADIUS client exists/updated with new IP
    add_radius_client(
        ip=mikrotik_ip,
        secret=RADIUS_SECRET,
        shortname=token
    )
    
    # Generate Config
    # version comes in as "7" or "6" from URL usually. 
    # Logic to parse version string if needed, user example was "7" or "v7"
    try:
        ver_int = int(version)
    except ValueError:
        # If version is like "v7", take valid int. Default to 7 if fails?
        # User script: [:local ver [:pick [/system resource get version] 0 1]] -> likely returns "6" or "7"
        if version.startswith('v'):
             version = version[1:]
        try:
            ver_int = int(version)
        except:
             ver_int = 7

    config_text = generate_mikrotik_config(
        shared_secret=RADIUS_SECRET,
        radius_ip="72.62.26.238", # Hardcoded per snippet/user
        nas_identifier=token, # User snippet: "nas_id=token"
        mikrotik_wan_ip=mikrotik_ip,
        routeros_version=ver_int,
        login_html=None, # Or fetch from elsewhere if needed
        status_html=None,
        tech_support_name="AlGaswaa Support",
        tech_support_phone="+249XXXXXXXX"
    )

    return HttpResponse(config_text, content_type="text/plain")
