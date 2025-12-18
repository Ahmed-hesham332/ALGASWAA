# offers/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Offer
from .forms import OfferForm


@login_required
def offer_list(request):
    user = request.user
    if user.is_distributer:
        distributer = user.distributer_profile
        if not distributer.can_view_offers:
            messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
            return redirect("dashboard:home")
        
        # Distributer sees his own offers ONLY
        offers = Offer.objects.filter(distributer=distributer)
    else:
        offers = Offer.objects.filter(reseller=user)
        
    return render(request, "dashboard/offers/offer_list.html", {"offers": offers})


@login_required
def offer_add(request):
    user = request.user
    reseller = user
    distributer = None
    
    if user.is_distributer:
        distributer = user.distributer_profile
        if not distributer.can_add_offer:
            messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
            return redirect("offers:offer_list")
        reseller = distributer.reseller

    if request.method == "POST":
        form = OfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.reseller = reseller
            if distributer:
                offer.distributer = distributer
            offer.save()
            messages.success(request, "تم إضافة العرض بنجاح.")
            return redirect("offers:offer_list")
    else:
        form = OfferForm()

    return render(request, "dashboard/offers/offer_add.html", {"form": form})


@login_required
def offer_edit(request, offer_id):
    user = request.user
    
    if user.is_distributer:
        distributer = user.distributer_profile
        if not distributer.can_edit_offer:
            messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
            return redirect("offers:offer_list")
        
        # Can only edit THEIR OWN offers
        # offer = get_object_or_404(Offer, id=offer_id, reseller=distributer.reseller, distributer=distributer)
        # Actually, let's checking ownership.
        offer = get_object_or_404(Offer, id=offer_id, reseller=distributer.reseller)
        if offer.distributer != distributer:
             messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
             return redirect("offers:offer_list")
            
    else:
        offer = get_object_or_404(Offer, id=offer_id, reseller=user)

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
    user = request.user
    
    if user.is_distributer:
        distributer = user.distributer_profile
        if not distributer.can_delete_offer:
            messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
            return redirect("offers:offer_list")
            
        offer = get_object_or_404(Offer, id=offer_id, reseller=distributer.reseller)
        if offer.distributer != distributer:
             messages.error(request, "ليس لديك الصلاحية للقيام بهذا الإجراء.")
             return redirect("offers:offer_list")
             
    else:
        offer = get_object_or_404(Offer, id=offer_id, reseller=user)
        
    offer.delete()
    messages.success(request, "تم حذف العرض.")
    return redirect("offers:offer_list")
