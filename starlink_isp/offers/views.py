# offers/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Offer
from .forms import OfferForm


@login_required
def offer_list(request):
    offers = Offer.objects.filter(reseller=request.user)
    return render(request, "dashboard/offers/offer_list.html", {"offers": offers})


@login_required
def offer_add(request):
    if request.method == "POST":
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.reseller = request.user
            offer.save()
            messages.success(request, "تم إضافة العرض بنجاح.")
            return redirect("offers:offer_list")
    else:
        form = OfferForm()

    return render(request, "dashboard/offers/offer_add.html", {"form": form})


@login_required
def offer_edit(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id, reseller=request.user)

    if request.method == "POST":
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل العرض بنجاح.")
            return redirect("offers:offer_list")
    else:
        form = OfferForm(instance=offer)

    return render(request, "dashboard/offers/offer_edit.html", {"form": form, "offer": offer})


@login_required
def offer_delete(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id, reseller=request.user)
    offer.delete()
    messages.success(request, "تم حذف العرض.")
    return redirect("offers:offer_list")
