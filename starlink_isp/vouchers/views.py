from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .utils import update_voucher_status
from django.utils import timezone
from .models import Voucher, VoucherBatch
from offers.models import Offer
from offers.models import Offer
from radius_integration.services import radius_add_user, voucher_radius_delete
from .forms import VoucherGenerationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from servers.models import Server
import string
import random

@login_required
def voucher_list(request):
    user = request.user
    
    if user.is_distributer:
        distributer = user.distributer_profile
        if not distributer.can_view_vouchers:
            messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
            return redirect("dashboard:home")
        vouchers = Voucher.objects.filter(batch__distributer=distributer)
        reseller = distributer.reseller
        servers = distributer.servers.all() # Distributer has assigned servers
        offers = Offer.objects.filter(distributer=distributer) # Distributer's own offers ONLY
        groups = VoucherBatch.objects.filter(distributer=distributer) # His batches
    else:
        vouchers = Voucher.objects.filter(batch__reseller=user)
        reseller = user
        servers = user.servers.all()
        offers = user.offers.all()
        groups = VoucherBatch.objects.filter(reseller=user)


    update_voucher_status()
    
    selected_server = request.GET.get("server", "")
    selected_offer = request.GET.get("offer", "")
    selected_group = request.GET.get("group", "")
    selected_status = request.GET.get("status", "")
    search_query = request.GET.get("search", "")

    # Filter by search query (serial)
    if search_query:
        vouchers = vouchers.filter(serial__icontains=search_query)

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

    # Server, offers, groups for dropdowns - Need to set is_selected
    # servers, offers, groups are already filtered above based on user/distributer
    for s in servers:
        s.is_selected = (str(s.id) == selected_server)

    for o in offers:
        o.is_selected = (str(o.id) == selected_offer)

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
    user = request.user
    reseller = user
    distributer = None
    
    if user.is_distributer:
        distributer = user.distributer_profile
        if not distributer.can_add_voucher:
             messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
             return redirect("vouchers:list")
        reseller = distributer.reseller

    
    if reseller.plan:  
        plan_limit = reseller.plan.number_of_vouchers
        # Count total vouchers for reseller (distributers count towards reseller quota)
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
        if distributer:
             form.fields['server'].queryset = distributer.servers.all()
             form.fields['offer'].queryset = Offer.objects.filter(distributer=distributer)

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

            # Check if Distributer has access to the server
            server = form.cleaned_data["server"]
            if distributer and server not in distributer.servers.all():
                 messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
                 return render(request, "dashboard/vouchers/voucher_add.html", {"form": form})

            batch = VoucherBatch.objects.create(
                reseller=reseller,
                distributer=distributer, # Link if exists
                server=server,
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
                    token=batch.server.hostname,
                    sold_price=batch.offer.price,
                )

                radius_add_user(serial, batch.offer, v.token)
                vouchers.append(v)

            messages.success(request, f"تم إنشاء {len(vouchers)} كارت بنجاح!")
            return redirect("vouchers:list")
    else:
        form = VoucherGenerationForm(reseller=reseller)
        if distributer:
            form.fields['server'].queryset = distributer.servers.all()
            form.fields['offer'].queryset = Offer.objects.filter(distributer=distributer)

    return render(request, "dashboard/vouchers/voucher_add.html", {"form": form})

@login_required
def batch_list(request):
    user = request.user
    
    if user.is_distributer:
        distributer = user.distributer_profile
        if not distributer.can_view_vouchers:
             messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
             return redirect("dashboard:home")
             
        batches = VoucherBatch.objects.filter(distributer=distributer).annotate(
            total_cards=Count('vouchers'),
            unused_cards=Count('vouchers', filter=Q(vouchers__is_used='unused')),
            used_cards=Count('vouchers', filter=Q(vouchers__is_used='used')),
            expired_cards=Count('vouchers', filter=Q(vouchers__is_used='expired'))
        ).order_by('-created_at')
    else:
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


@login_required
def reconnect_voucher(request, voucher_id):
    voucher = get_object_or_404(Voucher, id=voucher_id)

    # Security check: Ensure user owns this voucher (either as reseller or distributer)
    user = request.user
    if user.is_distributer:
        if voucher.batch.distributer != user.distributer_profile:
             messages.error(request, "ليس لديك صلاحية على هذا الكارت")
             return redirect("vouchers:list")
    else:
        if voucher.batch.reseller != user:
             messages.error(request, "ليس لديك صلاحية على هذا الكارت")
             return redirect("vouchers:list")

    if voucher.is_used != "unused":
        messages.error(request, "يمكن فقط إعادة توصيل الكروت غير المستخدمة.")
        return redirect("vouchers:list")

    try:
        # 1. Delete from Radius
        voucher_radius_delete(voucher.serial)
        
        # 2. Add back to Radius
        radius_add_user(voucher.serial, voucher.offer, voucher.token)
        
        messages.success(request, f"تم إعادة توصيل الكارت {voucher.serial} بنجاح.")
    except Exception as e:
        messages.error(request, f"حدث خطأ أثناء إعادة التوصيل: {e}")

    return redirect("vouchers:list")


@login_required
def delete_unused_vouchers(request, batch_id):
    batch = get_object_or_404(VoucherBatch, id=batch_id)
    user = request.user

    # Permission check
    if user.is_distributer:
        if batch.distributer != user.distributer_profile:
             messages.error(request, "ليس لديك صلاحية على هذه المجموعة")
             return redirect("vouchers:batch_list")
    else:
        if batch.reseller != user:
             messages.error(request, "ليس لديك صلاحية على هذه المجموعة")
             return redirect("vouchers:batch_list")

    # Get unused vouchers ONLY
    unused_vouchers = batch.vouchers.filter(is_used="unused")
    count_unused = unused_vouchers.count()
    
    # Calculate others (that will be preserved)
    count_others = batch.vouchers.exclude(is_used="unused").count()

    try:
        # 1. Delete Unused Vouchers
        for voucher in unused_vouchers:
            voucher_radius_delete(voucher.serial)
            voucher.delete()
        
        # 2. Delete the Batch
        # Because on_delete=SET_NULL, any remaining vouchers (used/expired) 
        # will validly remain in DB with batch=None.
        batch.delete()
        
        msg = f"تم حذف المجموعة بنجاح. تم حذف {count_unused} كارت غير مستخدم."
        if count_others > 0:
            msg += f" وتم الاحتفاظ بـ {count_others} كارت (مستخدم/منتهي) في الأرشيف."
            
        messages.success(request, msg)

    except Exception as e:
        messages.error(request, f"حدث خطأ أثناء الحذف: {e}")

    return redirect("vouchers:batch_list")
