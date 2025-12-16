# servers/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Server
from .forms import ServerForm
from radius_integration.services import generate_mikrotik_config, add_radius_client, radius_delete_client, voucher_radius_delete
from django.http import HttpResponse

@login_required
def server_list(request):
    servers = Server.objects.filter(owner=request.user)
    return render(request, "dashboard/servers/server_list.html", {"servers": servers})


@login_required
def server_download(request, server_id):
    server = get_object_or_404(Server, id=server_id, owner=request.user)

    # Define path to mikrotikUI folder
    from django.conf import settings
    import os

    mikrotik_ui_path = settings.BASE_DIR / "mikrotikUI"
    
    login_html = None
    status_html = None

    # Read login.html
    try:
        with open(mikrotik_ui_path / "login.html", "r", encoding="utf-8") as f:
            login_html = f.read()
    except FileNotFoundError:
        pass

    # Read status.html
    try:
        with open(mikrotik_ui_path / "status.html", "r", encoding="utf-8") as f:
            status_html = f.read()
    except FileNotFoundError:
        pass

    config_text = generate_mikrotik_config(
        shared_secret=server.api_password,
        radius_ip="72.62.26.238", 
        login_html=login_html,
        status_html=status_html
    )

    response = HttpResponse(config_text, content_type="text/plain")
    response["Content-Disposition"] = f'attachment; filename="Config_{server.id}.rsc"'
    return response


@login_required
def server_add(request):
    user = request.user

    if user.plan and Server.objects.filter(owner=user).count() >= user.plan.number_of_servers:
        messages.error(request, "لقد وصلت للحد الأقصى لعدد السيرفرات في خطتك.")
        return redirect("servers:list")

    if request.method == "POST":
        form = ServerForm(request.POST)
        if form.is_valid():
            server = form.save(commit=False)
            server.owner = user
            server.save()

            # ADD CLIENT TO FREERADIUS
            add_radius_client(
                ip=server.ip_address,
                secret=server.api_password,
                shortname=server.name.replace(" ", "_")
            )

            messages.success(request, "تم إضافة السيرفر")

            return redirect("servers:list")
    else:
        form = ServerForm()

    return render(request, "dashboard/servers/server_add.html", {"form": form})


@login_required
def server_edit(request, server_id):
    server = get_object_or_404(Server, id=server_id, owner=request.user)

    if request.method == "POST":
        form = ServerForm(request.POST, instance=server)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل السيرفر بنجاح.")
            return redirect("servers:list")
    else:
        form = ServerForm(instance=server)

    return render(request, "dashboard/servers/server_edit.html", {"form": form, "server": server})


@login_required
def server_delete(request, server_id):
    server = get_object_or_404(Server, id=server_id, owner=request.user)

    # DELETE VOUCHERS FROM RADIUS
    vouchers = server.voucher_set.all()
    for voucher in vouchers:
        voucher_radius_delete(voucher.serial)
        voucher.delete()

    # DELETE FROM RADIUS NAS TABLE
    radius_delete_client(server.ip_address)
    
    # DELETE FROM DJANGO
    server.delete()

    messages.success(request, "تم حذف السيرفر")
    return redirect("servers:list")