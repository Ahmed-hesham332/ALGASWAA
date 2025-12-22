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

    # Bootstrap Script
    domain = "72.62.26.238"
    # routeros fetch command
    # Assuming token is available as property on server
    fetch_script = f"""
[:local ver [:pick  [/system resource get version] 0 1];
/tool fetch url="http://{domain}/radius-integration/api/install/{server.install_token}/$ver/" dst-path="algaswaa.rsc";
:delay 5;
/import file-name=algaswaa.rsc;
]
"""
    response = HttpResponse(fetch_script, content_type="text/plain")
    response["Content-Disposition"] = f'attachment; filename="AlGaswaa_Install_{server.id}.rsc"'
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

            # Add to RADIUS using NAS-Identifier (token)
            from radius_integration.services import RADIUS_SECRET
            add_radius_client(
                hostname=server.install_token,
                shortname=server.name,
                secret=RADIUS_SECRET
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
    radius_delete_client(server.hostname)
    
    # DELETE FROM DJANGO
    server.delete()

    messages.success(request, "تم حذف السيرفر")
    return redirect("servers:list")