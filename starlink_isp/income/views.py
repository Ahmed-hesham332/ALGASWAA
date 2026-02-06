from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from vouchers.models import Voucher
from servers.models import Server
from django.db.models import Count, Sum, F

@login_required
def income_report(request):
    user = request.user

    # 🔹 FILTERS
    server_id = request.GET.get("server", "all")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    vouchers = Voucher.objects.filter(server__owner=user)

    # ---- Server Filter ----
    servers = Server.objects.filter(owner=user)
    for s in servers:
        s.is_selected = (str(s.id) == server_id)

    if server_id != "all":
        vouchers = vouchers.filter(server_id=server_id)

    # ---- Date Filter ----
    if date_from:
        vouchers = vouchers.filter(activated_at__date__gte=date_from)

    if date_to:
        vouchers = vouchers.filter(activated_at__date__lte=date_to)

    # ---- Only SOLD vouchers ----
    sold_vouchers = vouchers.exclude(is_used="unused")

    # ---- TOTALS ----
    total_count = sold_vouchers.count()
    # Use the static sold_price field
    total_income = sum(v.sold_price for v in sold_vouchers)

    # ---- DAILY SUMMARY ----
    daily_summary = (
        sold_vouchers
        .values("activated_at__date")
        .annotate(
            count=Count("id"),
            income=Sum("sold_price")
        )
        .order_by("activated_at__date")
    )

    summary = [
        {
            "day": row["activated_at__date"],
            "count": row["count"],
            "income": row["income"],
        }
        for row in daily_summary
    ]

    return render(request, "dashboard/income/income.html", {
        "servers": servers,
        "selected_server": server_id,
        "summary": summary,
        "total_count": total_count,
        "total_income": total_income,
        "date_from": date_from,
        "date_to": date_to,
    })
