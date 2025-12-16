from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from account.models import CustomUser
from .forms import ProfileForm, PasswordChangeCustomForm


@login_required
def profile_view(request):

    user = request.user

    # Handle info update
    if request.method == "POST" and "save_info" in request.POST:
        form = ProfileForm(request.POST, instance=user)
        pass_form = PasswordChangeCustomForm()  # empty form for display only

        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث المعلومات بنجاح")
            return redirect("profile:profile")

    else:
        form = ProfileForm(instance=user)
        pass_form = PasswordChangeCustomForm()

    # Handle password change
    if request.method == "POST" and "change_password" in request.POST:
        form = ProfileForm(instance=user)
        pass_form = PasswordChangeCustomForm(request.POST)

        if pass_form.is_valid():
            old = pass_form.cleaned_data["old_password"]
            if not user.check_password(old):
                messages.error(request, "كلمة المرور القديمة غير صحيحة")
                return redirect("profile:profile")

            user.set_password(pass_form.cleaned_data["new_password"])
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "تم تغيير كلمة المرور بنجاح")
            return redirect("profile:profile")

    return render(request, "dashboard/profile/profile.html", {
        "form": form,
        "pass_form": pass_form,
    })
