def get_client_ip(request):
    """
    Get real client IP behind proxy (Hostinger / Nginx / Docker).
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # first IP is the real client
        return x_forwarded_for.split(",")[0].strip()

    real_ip = request.META.get("HTTP_X_REAL_IP")
    if real_ip:
        return real_ip

    return request.META.get("REMOTE_ADDR")
