# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import LoginForm

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect("adminpanel:tech_support_list")
        if hasattr(request.user, "tech_support_profile"):
            return redirect("adminpanel:reseller_list")
        return redirect("dashboard:home")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"]
        )

        if user:
            login(request, user)

            if user.is_superuser:
                return redirect("adminpanel:tech_support_list")

            if hasattr(user, "tech_support_profile"):
                return redirect("adminpanel:reseller_list")

            return redirect("dashboard:home")

        messages.error(request, "خطأ في اسم المستخدم أو كلمة المرور")

    return render(request, "landingPage/login.html", {"form": form})



def logout_view(request):
    logout(request)
    return redirect("login")



