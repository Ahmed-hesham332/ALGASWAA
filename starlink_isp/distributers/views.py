from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import DistributerUserForm, DistributerPermissionsForm
from .models import Distributer
from servers.models import Server

@login_required
def distributer_list(request):
    distributers = Distributer.objects.filter(reseller=request.user)
    return render(request, "dashboard/distributers/distributer_list.html", {"distributers": distributers})

@login_required
def distributer_add(request):
    user_form = DistributerUserForm(request.POST or None)
    perm_form = DistributerPermissionsForm(reseller=request.user, data=request.POST or None)

    if request.method == "POST":
        if user_form.is_valid() and perm_form.is_valid():
            user = user_form.save(commit=False)
            if user_form.cleaned_data["password"]:
                user.set_password(user_form.cleaned_data["password"])
            user.save()

            distributer = perm_form.save(commit=False)
            distributer.user = user
            distributer.reseller = request.user
            distributer.save()
            perm_form.save_m2m() # Important for servers

            messages.success(request, "تم إضافة الموزع بنجاح")
            return redirect("distributers:distributer_list")

    return render(request, "dashboard/distributers/distributer_add.html", {
        "user_form": user_form,
        "perm_form": perm_form,
        "title": "إضافة موزع جديد"
    })

@login_required
def distributer_edit(request, pk):
    distributer = get_object_or_404(Distributer, pk=pk, reseller=request.user)
    user = distributer.user
    
    user_form = DistributerUserForm(request.POST or None, instance=user)
    perm_form = DistributerPermissionsForm(reseller=request.user, data=request.POST or None, instance=distributer)

    if request.method == "POST":
        if user_form.is_valid() and perm_form.is_valid():
            user = user_form.save(commit=False)
            if user_form.cleaned_data["password"]:
                user.set_password(user_form.cleaned_data["password"])
            
            # Since we are using user_form.save(commit=False), we receive the instance with new data.
            # If the password field was left empty, cleaned_data['password'] is empty.
            if user_form.cleaned_data.get("password"):
                user.set_password(user_form.cleaned_data["password"])
            
            user.save()
            perm_form.save()
            
            messages.success(request, "تم تعديل بيانات الموزع بنجاح")
            return redirect("distributers:distributer_list")

    return render(request, "dashboard/distributers/distributer_edit.html", {
        "user_form": user_form,
        "perm_form": perm_form,
        "distributer": distributer,
        "title": "تعديل بيانات الموزع"
    })

@login_required
def distributer_delete(request, pk):
    distributer = get_object_or_404(Distributer, pk=pk, reseller=request.user)
    user = distributer.user
    user.delete() # Cascades to Distributer
    messages.success(request, "تم حذف الموزع بنجاح")
    return redirect("distributers:distributer_list")
