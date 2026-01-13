# servers/utils.py
import ipaddress
from .models import Server

TUNNEL_NET = ipaddress.ip_network("172.26.0.0/20")
RESERVED = {TUNNEL_NET.network_address, TUNNEL_NET.broadcast_address, ipaddress.ip_address("172.26.0.1")}

def allocate_tunnel_ip():
    used = set(Server.objects.exclude(tunnel_ip__isnull=True).values_list("tunnel_ip", flat=True))
    used = {ipaddress.ip_address(ip) for ip in used}
    for ip in TUNNEL_NET.hosts():
        if ip in RESERVED:
            continue
        if ip < ipaddress.ip_address("172.26.0.10"):
            continue
        if ip not in used:
            return str(ip)
    raise RuntimeError("No tunnel IPs available")
