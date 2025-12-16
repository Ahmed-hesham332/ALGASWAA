from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .utils import update_voucher_status
from django.utils import timezone
from .models import Voucher, VoucherBatch
from radius_integration.services import radius_add_user
from .forms import VoucherGenerationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from servers.models import Server
import string
import random

def voucher_list(request):
    user = request.user

    vouchers = Voucher.objects.filter(batch__reseller=user)


    update_voucher_status()
    
    selected_server = request.GET.get("server", "")
    selected_offer = request.GET.get("offer", "")
    selected_group = request.GET.get("group", "")
    selected_status = request.GET.get("status", "")

    # Filter by server
    if selected_server:
        vouchers = vouchers.filter(server_id=selected_server)

    # Filter by offer
    if selected_offer:
        vouchers = vouchers.filter(offer_id=selected_offer)

    # Filter by batch/group
    if selected_group:
        vouchers = vouchers.filter(batch_id=selected_group)

    # Status filters (STRING-BASED LOGIC)
    now = timezone.now()

    if selected_status == "unused":
        vouchers = vouchers.filter(is_used="unused")

    elif selected_status == "used":
        vouchers = vouchers.filter(is_used="used")

    elif selected_status == "expired":
        vouchers = vouchers.filter(expires_at__lt=now)

    elif selected_status == "active":
        vouchers = vouchers.filter(is_used="used", expires_at__gte=now)

    # Server, offers, groups for dropdowns
    servers = user.servers.all()
    for s in servers:
        s.is_selected = (str(s.id) == selected_server)

    offers = user.offers.all()
    for o in offers:
        o.is_selected = (str(o.id) == selected_offer)

    groups = VoucherBatch.objects.filter(reseller=user)
    for g in groups:
        g.is_selected = (str(g.id) == selected_group)

    statuses = {
        "used": selected_status == "مُستخدم",
        "unused": selected_status == "غير مستخدم",
        "expired": selected_status == "منتهي"
    }

    # PAGINATION — 50 per page
    paginator = Paginator(vouchers, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "vouchers": page_obj,
        "servers": servers,
        "offers": offers,
        "groups": groups,
        "statuses": statuses,
    }

    return render(request, "dashboard/vouchers/voucher_list.html", context)

    
@login_required
def voucher_generate(request):
    reseller = request.user

    
    if reseller.plan:  
        plan_limit = reseller.plan.number_of_vouchers
        current_vouchers = Voucher.objects.filter(batch__reseller=reseller).count()

        if current_vouchers >= plan_limit:
            messages.error(
                request,
                "لقد وصلت إلى الحد الأقصى لعدد الكروت المسموح بها في خطتك. "
                "قم بالترقية لزيادة الحد."
            )
            return redirect("vouchers:list")

    if request.method == "POST":
        form = VoucherGenerationForm(request.POST, reseller=reseller)
        if form.is_valid():

            quantity = form.cleaned_data["quantity"]

            if reseller.plan:
                plan_limit = reseller.plan.number_of_vouchers
                current = Voucher.objects.filter(batch__reseller=reseller).count()

                if current + quantity > plan_limit:
                    messages.error(
                        request,
                        f"لا يمكنك إنشاء {quantity} كارت. "
                        f"لقد تبقى لك فقط {plan_limit - current} كروت في خطتك."
                    )
                    return render(request, "dashboard/vouchers/voucher_add.html", {"form": form})

            batch = VoucherBatch.objects.create(
                reseller=reseller,
                server=form.cleaned_data["server"],
                offer=form.cleaned_data["offer"],
                name=form.cleaned_data["name"],
                quantity=form.cleaned_data["quantity"],
                prefix=form.cleaned_data["prefix"],
                serial_length=form.cleaned_data["serial_length"],
                serial_type=form.cleaned_data["serial_type"]
            )

            # Create vouchers
            vouchers = []
            for _ in range(batch.quantity):
                serial = generate_serial(
                    length=batch.serial_length,
                    type=batch.serial_type,
                    prefix=batch.prefix,
                )

                v = Voucher.objects.create(
                    batch=batch,
                    server=batch.server,
                    offer=batch.offer,
                    serial=serial,
                    ip_address=batch.server.ip_address,
                )

                radius_add_user(serial, batch.offer, v.ip_address)
                vouchers.append(v)

            messages.success(request, f"تم إنشاء {len(vouchers)} كارت بنجاح!")
            return redirect("vouchers:list")

    else:
        form = VoucherGenerationForm(reseller=reseller)

    return render(request, "dashboard/vouchers/voucher_add.html", {"form": form})

@login_required
def batch_list(request):
    user = request.user
    
    batches = VoucherBatch.objects.filter(reseller=user).annotate(
        total_cards=Count('vouchers'),
        unused_cards=Count('vouchers', filter=Q(vouchers__is_used='unused')),
        used_cards=Count('vouchers', filter=Q(vouchers__is_used='used')),
        expired_cards=Count('vouchers', filter=Q(vouchers__is_used='expired'))
    ).order_by('-created_at')

    # Pagination - 20 per page as requested
    paginator = Paginator(batches, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "batches": page_obj,
        "page_obj": page_obj
    }
    return render(request, "dashboard/vouchers/batch_list.html", context)


def generate_serial(length, type, prefix=""):
    if type == "numeric":
        body = ''.join(random.choices(string.digits, k=length))
    else:
        chars = string.ascii_uppercase + string.digits
        body = ''.join(random.choices(chars, k=length))

    return prefix + body
