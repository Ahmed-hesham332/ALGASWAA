from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from servers.models import Server

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

    server.last_heartbeat = timezone.now()
    server.save(update_fields=['last_heartbeat'])

    return JsonResponse({"status": "ok", "server": server.name})
