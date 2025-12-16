# dashboard/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connections
from vouchers.models import Voucher
from servers.models import Server
from adminpanel.models import TechSupport
from django.utils import timezone
from datetime import date


def get_online_voucher_count(user):
    """
    Count active sessions for vouchers belonging to this reseller.
    """

    # 1️⃣ Get all voucher serials belonging to this reseller
    valid_serials = list(
        Voucher.objects.filter(batch__reseller=user)
        .values_list("serial", flat=True)
    )

    if not valid_serials:
        return 0

    # 2️⃣ Query RADIUS to count active online sessions
    cursor = connections["radius"].cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM radacct
        WHERE acctstoptime IS NULL
        AND username IN %s
    """, [tuple(valid_serials)])

    result = cursor.fetchone()[0]
    return result or 0


def get_next_payment_date(today_date: date) -> date:
    """
    Calculates the next payment date, set to the 5th of the month.
    If today is past the 5th, it returns the 5th of the next month.
    Otherwise, it returns the 5th of the current month.
    """
    PAYMENT_DAY = 5

    if today_date.day > PAYMENT_DAY:
        # Today is past the 5th, payment is the 5th of the NEXT month.
        
        # Calculate the next month (handling year transition)
        next_month = today_date.month + 1
        next_year = today_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1
            
        return date(next_year, next_month, PAYMENT_DAY)
        
    else:
        # Today is the 5th or earlier, payment is the 5th of the CURRENT month.
        return date(today_date.year, today_date.month, PAYMENT_DAY)


@login_required
def home(request):
    user = request.user
    tech_support = getattr(user, 'tech_support_assigned', None)
    if not tech_support:
        tech_support = TechSupport.objects.first()
    plan = user.plan
    today = timezone.localdate()
    
   
    total_vouchers_created = Voucher.objects.filter(batch__reseller=user).count()
    online_vouchers = get_online_voucher_count(user)
    total_servers = Server.objects.filter(owner=user).count()

    next_payment_date = get_next_payment_date(today)

    return render(request, "dashboard/base.html", {
        "tech_support": tech_support,
        "user": user,
        "plan": plan,
        "total_vouchers_created": total_vouchers_created,
        "online_vouchers": online_vouchers,
        "total_servers": total_servers,
        "next_payment_date": next_payment_date,
    })