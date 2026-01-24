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

    cursor = connections['radius'].cursor()
    cursor.execute("""
        SELECT 
            data
        FROM vouchers
        WHERE voucher_number = %s
    """, [username])

    data = cursor.fetchone()

    offer = voucher.offer

    usage_bytes = data[0] if data else 0
    mb_used = 0 if usage_bytes == 0 else usage_bytes / (1024 * 1024) 
    mb_used = round(mb_used, 2)
    
    # 1. Determine Quota in MB
    if offer.quota_type == 'none':
        quota_mb = None  # Unlimited
    elif offer.quota_type == 'MB':
        quota_mb = offer.quota_amount
    else:
        # Default to GB -> MB
        quota_mb = offer.quota_amount * 1024

    # 2. Calculate Remaining & Percentage
    if quota_mb is None:
        remaining_mb = None # Unlimited
    else:
        remaining_mb = max(0, quota_mb - mb_used)

    # 7️⃣ Return useful data
    return {
        "username": username,
        "used_mb": mb_used,    
        "remaining_mb": round(remaining_mb, 2) if remaining_mb is not None else None,
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

