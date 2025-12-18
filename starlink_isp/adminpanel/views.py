from radius_integration.services import radius_suspend_unused_vouchers, radius_unsuspend_unused_vouchers, voucher_radius_delete, radius_delete_client
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from account.models import CustomUser
from servers.models import Server
from .models import Plan, TechSupport
from .forms import ResellerForm, PlanForm, TechSupportForm, TechSupportUserForm
from django.http import JsonResponse
from django.db.models import Q

def admin_only(user):
    return user.is_superuser

def tech_support_only(user):
    return (
        user.is_authenticated and
        hasattr(user, "tech_support_profile")
    )
# --------------------------
# Tech Support Views
# --------------------------    
    
@user_passes_test(tech_support_only)
def reseller_toggle_status(request, reseller_id):
    reseller = get_object_or_404(
        CustomUser,
        id=reseller_id,
        tech_support_assigned__user=request.user
    )

    reseller.status = not reseller.status
    reseller.save()

    if reseller.status:
        radius_unsuspend_unused_vouchers(reseller)
    else:
        radius_suspend_unused_vouchers(reseller)

    return redirect("adminpanel:reseller_list")

@user_passes_test(tech_support_only)
def reseller_toggle_paied(request, reseller_id):
    reseller = get_object_or_404(
        CustomUser,
        id=reseller_id,
        tech_support_assigned__user=request.user
    )

    reseller.has_paied = not reseller.has_paied
    reseller.save()

    return redirect("adminpanel:reseller_list")


@user_passes_test(tech_support_only)
def reseller_list(request):
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")
    has_paied_filter = request.GET.get("has_paied", "")

    resellers = CustomUser.objects.filter(tech_support_assigned__user=request.user)

    if q:
        resellers = resellers.filter(id=q)
    
    if status_filter in ["True", "False"]:
        resellers = resellers.filter(status=(status_filter == "True"))
    
    if has_paied_filter in ["True", "False"]:
        resellers = resellers.filter(has_paied=(has_paied_filter == "True"))

    statuses = {
        "active": status_filter == "True",
        "inactive": status_filter == "False",
    }

    payments = {
        "paid": has_paied_filter == "True",
        "not_paid": has_paied_filter == "False",
    }

    return render(
        request,
        "admin/techsupport/reseller_list.html",
        {
            "resellers": resellers,
            "q": q,
            "statuses": statuses,
            "payments": payments,
            "status_filter": status_filter,
            "has_paied_filter": has_paied_filter,
        }
    )   


@user_passes_test(tech_support_only)
def reseller_add(request):
    if request.method == "POST":
        form = ResellerForm(request.POST)
        if form.is_valid():
            reseller = form.save(commit=False)

            if form.cleaned_data["password"]:
                reseller.set_password(form.cleaned_data["password"])

            reseller.is_staff = False
            reseller.tech_support_assigned = request.user.tech_support_profile
            reseller.save()

            messages.success(request, "تم إضافة موزع جديد.")
            return redirect("adminpanel:reseller_list")
    else:
        form = ResellerForm()

    return render(request, "admin/techsupport/reseller_add.html", {"form": form})


@user_passes_test(tech_support_only)
def reseller_edit(request, user_id):
    reseller = get_object_or_404(
        CustomUser,
        id=user_id,
        tech_support_assigned__user=request.user
    )

    form = ResellerForm(request.POST or None, instance=reseller)

    if request.method == "POST" and form.is_valid():
        reseller = form.save(commit=False)

        if form.cleaned_data["password"]:
            reseller.set_password(form.cleaned_data["password"])

        reseller.save()
        messages.success(request, "تم تعديل بيانات الموزع.")
        return redirect("adminpanel:reseller_list")

    return render(request, "admin/techsupport/reseller_edit.html", {
        "form": form,
        "reseller": reseller
    })



@user_passes_test(tech_support_only)
def reseller_delete(request, user_id):
    reseller = get_object_or_404(
        CustomUser,
        id=user_id,
        tech_support_assigned__user=request.user
    )

    servers = reseller.servers.all()
    for server in servers:
        vouchers = server.voucher_set.all()
        for voucher in vouchers:
            voucher_radius_delete(voucher.serial)
            voucher.delete()
        
        radius_delete_client(server.ip_address)
        server.delete()

    reseller.delete()
    messages.success(request, "تم حذف الموزع.")
    return redirect("adminpanel:reseller_list")


@user_passes_test(tech_support_only)
def delete_unpaid_resellers(request):
    """
    Delete all resellers (CustomUser) assigned to the current tech support user
    who have has_paied=False.
    """
    # 1. Get all unpaid resellers for this tech support
    unpaid_resellers = CustomUser.objects.filter(
        tech_support_assigned__user=request.user,
        has_paied=False
    )

    count = unpaid_resellers.count()

    if count == 0:
        messages.warning(request, "لا يوجد مشتركين غير مدفوعين لحذفهم.")
        return redirect("adminpanel:reseller_list")

    # 2. Iterate and delete each one (handling servers/radius cleanup)
    #    We duplicate logic from reseller_delete or call it if it were a service function.
    #    Since reseller_delete logic is embedded in the view, we replicate it here.
    
    for reseller in unpaid_resellers:
        # Cleanup servers -> vouchers -> radius
        servers = reseller.servers.all()
        for server in servers:
            vouchers = server.voucher_set.all()
            for voucher in vouchers:
                voucher_radius_delete(voucher.serial)
                # voucher.delete() # cascade should handle this, but explicit is fine

            radius_delete_client(server.ip_address)
            # server.delete() # cascade should handle this

        # Finally delete the user
        reseller.delete()

    messages.success(request, f"تم حذف {count} مشتركين غير مدفوعين بنجاح.")
    return redirect("adminpanel:reseller_list")


@user_passes_test(tech_support_only)
def server_delete(request, server_id):
    server = get_object_or_404(
        Server,
        id=server_id,
        owner__tech_support_assigned__user=request.user
    )

    # 1. Delete Vouchers from RADIUS
    vouchers = server.voucher_set.all()
    for voucher in vouchers:
        voucher_radius_delete(voucher.serial)

    # 2. Delete NAS Client from RADIUS
    radius_delete_client(server.hostname)
    
    # 3. Delete from Django
    server.delete()
    messages.success(request, "تم حذف الخادم.")
    return redirect("adminpanel:server_list")


@user_passes_test(tech_support_only)
def server_list(request):
    resellers = CustomUser.objects.filter(
        tech_support_assigned__user=request.user
    )

    servers = Server.objects.filter(owner__in=resellers)

    search_query = request.GET.get("search", "")

    if search_query:
        servers = servers.filter(
            Q(name__icontains=search_query) |
            Q(owner__username__icontains=search_query)
        )

    return render(request, "admin/techsupport/server_list.html", {
        "servers": servers,
        "search": search_query
    })


@user_passes_test(tech_support_only)
def profile(request):
    tech_profile = request.user.tech_support_profile
    profile_form = TechSupportForm(
        request.POST or None,
        instance=tech_profile
    )

    if request.method == "POST" and profile_form.is_valid():
        profile = profile_form.save(commit=False)
        profile.phone = whatsapp_phone(profile.phone)
        profile.save()

        messages.success(request, "تم تحديث الملف الشخصي")
        return redirect("adminpanel:reseller_list")

    return render(request, "admin/techsupport/my_profile_edit.html", {
        "profile_form": profile_form
    })


# --------------------------
# Plans
# --------------------------

@user_passes_test(admin_only)
def plan_list(request):
    plans = Plan.objects.all()
    return render(request, "admin/superuser/plan_list.html", {"plans": plans})


@user_passes_test(admin_only)
def plan_add(request):
    form = PlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم إضافة الخطة.")
        return redirect("adminpanel:plan_list")

    return render(request, "admin/superuser/plan_add.html", {"form": form})


@user_passes_test(admin_only)
def plan_edit(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    form = PlanForm(request.POST or None, instance=plan)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تعديل الخطة.")
        return redirect("adminpanel:plan_list")

    return render(request, "admin/superuser/plan_edit.html", {"form": form, "plan": plan})


@user_passes_test(admin_only)
def plan_delete(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    plan.delete()
    messages.success(request, "تم حذف الخطة.")
    return redirect("adminpanel:plan_list")

# -------------------------
#
# Technical Support (SuperAdmin Views)
#
# -------------------------
def whatsapp_phone(phone):
    if phone:
        return phone.replace("+", "").replace(" ", "")
    return ""

@user_passes_test(admin_only)
def tech_support_list(request):
    tech_supports = TechSupport.objects.select_related("user")
    return render(
        request,
        "admin/superuser/tech_support_list.html",
        {"tech_supports": tech_supports}
    )

@user_passes_test(admin_only)
def tech_support_add(request):
    user_form = TechSupportUserForm(request.POST or None)
    profile_form = TechSupportForm(request.POST or None)

    if request.method == "POST":
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data["password"])
            user.is_staff = True
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()

            messages.success(request, "تم إضافة حساب الدعم الفني")
            return redirect("adminpanel:tech_support_list")

    return render(request, "admin/superuser/tech_support_add.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })



@user_passes_test(admin_only)
def tech_support_edit(request, tech_id):
    tech = get_object_or_404(TechSupport, id=tech_id)
    user_form = TechSupportUserForm(request.POST or None, instance=tech.user)
    profile_form = TechSupportForm(request.POST or None, instance=tech)
    
    if request.method == "POST":
        if profile_form.is_valid():
            p = profile_form.save(commit=False)
            p.phone = whatsapp_phone(p.phone)
            p.save()
            
            messages.success(request, "تم تعديل حساب الدعم الفني")
            return redirect("adminpanel:tech_support_list")

    return render(request, "admin/superuser/tech_support_add.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })

@user_passes_test(admin_only)
def tech_support_delete(request, tech_id):
    tech = get_object_or_404(TechSupport, id=tech_id)
    # Delete the user, which cascades to delete the TechSupport profile
    tech.user.delete()
    messages.success(request, "تم حذف حساب الدعم الفني")
    return redirect("adminpanel:tech_support_list")



@user_passes_test(admin_only)
def all_server_list(request):
    servers = Server.objects.all().select_related("owner", "owner__tech_support_assigned")
    
    search_query = request.GET.get("search", "")

    if search_query:
        servers = servers.filter(
            Q(name__icontains=search_query) |
            Q(owner__username__icontains=search_query) |
            Q(owner__tech_support_assigned__user__username__icontains=search_query) | 
            Q(owner__tech_support_assigned__name__icontains=search_query)
        )

    return render(request, "admin/superuser/all_server_list.html", {
        "servers": servers,
        "search": search_query
    })
