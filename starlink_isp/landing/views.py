from django.shortcuts import render
from adminpanel.models import Plan

def landing_index(request):
    plans = Plan.objects.all()
    return render(request, "landingPage/index.html", {"plans": plans})
