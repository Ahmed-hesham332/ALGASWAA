from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from servers.models import Server
from ..utils import get_client_ip
from ..services import add_radius_client, RADIUS_SECRET

def mikrotik_heartbeat(request, token):
    """
    Receives heartbeat from MikroTik.
    Token format: {owner_id}_{server_id}
    """
    try:
        owner_id, server_id = token.split('_')
    except ValueError:
        raise Http404("Invalid token format")

    server = get_object_or_404(
        Server,
        id=server_id,
        owner_id=owner_id
    )

    # ✅ CAPTURE REAL IP
    mikrotik_ip = get_client_ip(request)

    # Update server WAN IP
    if mikrotik_ip:
        server.ip_address = mikrotik_ip
    
    server.last_heartbeat = timezone.now()
    server.save(update_fields=['last_heartbeat', 'ip_address'])

    # ✅ SYNC TO RADIUS NAS
    if mikrotik_ip:
        add_radius_client(
            nasname=mikrotik_ip,
            shortname=token,      
            secret=RADIUS_SECRET
        )

    return JsonResponse({"status": "ok", "server": server.name})
