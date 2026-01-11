from django.db import connections, transaction
from django.shortcuts import get_object_or_404
from vouchers.models import Voucher
from django.http import JsonResponse
from django.views.decorators.http import require_GET

def update_voucher_usage(username):
    """
    Calculates total used data from radacct,
    updates voucher.usage_mb,
    and returns usage/limit information.
    """

    voucher = get_object_or_404(Voucher, serial=username)

    offer = voucher.offer
    
    # 1. Determine Quota in MB
    if offer.quota_type == 'none':
        quota_mb = None  # Unlimited
    elif offer.quota_type == 'MB':
        quota_mb = offer.quota_amount
    else:
        # Default to GB
        quota_mb = (offer.quota_amount or 0) * 1024

    with connections["radius"].cursor() as cursor:
        cursor.execute("""
            SELECT COALESCE(SUM(acctinputoctets + acctoutputoctets), 0)
            FROM radacct
            WHERE username = %s
        """, [username])

        used_bytes = cursor.fetchone()[0]

    used_mb = round(used_bytes / 1024 / 1024, 2)

    voucher.usage_mb = used_mb
    voucher.save(update_fields=["usage_mb"])

    # 2. Calculate Remaining & Percentage
    if quota_mb is None:
        remaining_mb = None # Unlimited
        percentage = 0
    else:
        remaining_mb = max(0, quota_mb - used_mb)
        percentage = round((used_mb / quota_mb) * 100, 2) if quota_mb > 0 else 0

    # 7️⃣ Return useful data
    return {
        "username": username,
        "used_mb": used_mb,
        "quota_mb": quota_mb,
        "remaining_mb": round(remaining_mb, 2) if remaining_mb is not None else None,
        "percentage": percentage,
    }

@require_GET
def voucher_usage_view(request):
    username = request.GET.get("username")
    
    if not username:
        return JsonResponse({"error": "Missing username parameter"}, status=400)
    
    try:
        data = update_voucher_usage(username)
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=404)

